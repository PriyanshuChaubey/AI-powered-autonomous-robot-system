"""
llm.py - one small client for every agent.

Three modes, chosen by env var FIRM_LLM_MODE:
  mock    (default)  -> returns the golden outputs in mock_data.py. No network, no API key.
  openai             -> any OpenAI-compatible /chat/completions endpoint (OpenAI, Groq, Together, vLLM)
  ollama             -> a local Ollama server

Env vars:
  FIRM_LLM_MODE=mock|openai|ollama
  FIRM_LLM_BASE_URL  default https://api.openai.com/v1
  FIRM_LLM_MODEL     default gpt-4o-mini (mock ignores it)
  FIRM_LLM_API_KEY   required for openai mode
  FIRM_LLM_TEMPERATURE default 0.2
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMError(RuntimeError):
    pass


@dataclass
class LLMClient:
    mode: str
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.2
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "LLMClient":
        return cls(
            mode=os.getenv("FIRM_LLM_MODE", "mock").strip().lower(),
            base_url=os.getenv("FIRM_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.getenv("FIRM_LLM_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("FIRM_LLM_API_KEY", ""),
            temperature=float(os.getenv("FIRM_LLM_TEMPERATURE", "0.2")),
        )

    # ------------------------------------------------------------------ raw
    def complete(self, system: str, user: str) -> str:
        if self.mode == "mock":
            raise LLMError("mock mode has no generic completion - call complete_json with a mock_key")

        if self.mode == "openai":
            if not self.api_key:
                raise LLMError("FIRM_LLM_API_KEY is not set for openai mode")
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            payload = {
                "model": self.model,
                "temperature": self.temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        elif self.mode == "ollama":
            url = f"{self.base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "temperature": self.temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        else:
            raise LLMError(f"unknown FIRM_LLM_MODE: {self.mode!r}")

        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise LLMError(f"HTTP {exc.code} from {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"cannot reach {url}: {exc.reason}") from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"unexpected response shape: {str(body)[:400]}") from exc

    # --------------------------------------------------------------- json io
    def complete_json(
        self,
        system: str,
        user: str,
        mock_key: str | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Ask for JSON, parse it, and on failure tell the model what broke."""
        if self.mode == "mock":
            from mock_data import MOCKS

            if mock_key not in MOCKS:
                raise LLMError(f"no mock registered for {mock_key!r}")
            return json.loads(json.dumps(MOCKS[mock_key]))  # deep copy

        last_error = ""
        bad_output = ""
        for attempt in range(1, retries + 1):
            prompt = user
            if attempt > 1:
                prompt += (
                    "\n\nYour previous reply could not be parsed as JSON.\n"
                    f"Error: {last_error}\n"
                    f"Previous reply:\n{bad_output[:2000]}\n"
                    "Return ONLY the JSON object. No markdown fences, no commentary."
                )
            raw = self.complete(system, prompt)
            try:
                return _extract_json(raw)
            except ValueError as exc:
                last_error = str(exc)
                bad_output = raw
        raise LLMError(f"model did not return valid JSON after {retries} tries: {last_error}")


_JSON_START = re.compile(r"[\[{]")


def _extract_json(text: str) -> dict[str, Any]:
    """Tolerate ```json fences and stray prose around the object."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_START.search(text)
        if not match:
            raise ValueError("no JSON object found in reply")
        try:
            value, _ = json.JSONDecoder().raw_decode(text[match.start():])
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object, got {type(value).__name__}")
    return value
