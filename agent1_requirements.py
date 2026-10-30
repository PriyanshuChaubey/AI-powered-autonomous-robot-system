"""
agent1_requirements.py - Agent 1 of the firmware pipeline.

    free-text mission  ->  structured, testable requirements (JSON)

The output is the contract every later agent reads. Nothing downstream is
allowed to fetch its own context: if Agent 2 needs to know a distance
threshold, it comes from here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import prompts
from llm import LLMClient

REQUIRED_KEYS = (
    "project",
    "mission",
    "functional_requirements",
    "non_functional_requirements",
    "hardware_requirements",
    "interfaces",
    "acceptance_tests",
    "assumptions",
    "open_questions",
)


def run(mission: str, catalog: dict[str, Any], llm: LLMClient, out_path: Path) -> dict[str, Any]:
    result = llm.complete_json(
        system=prompts.A1_SYSTEM,
        user=prompts.a1_user(mission, catalog),
        mock_key="requirements",
    )

    _validate_shape(result)

    result["_meta"] = {
        "agent": "agent1_requirements",
        "model_mode": llm.mode,
        "model": llm.model if llm.mode != "mock" else "golden-example",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_mission_chars": len(mission),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _validate_shape(req: dict[str, Any]) -> None:
    """Block the stage if the contract is not met - do not pass a half-spec on."""
    missing = [k for k in REQUIRED_KEYS if k not in req]
    if missing:
        raise ValueError(f"Agent 1 output is missing keys: {missing}")

    if len(req["functional_requirements"]) < 3:
        raise ValueError("Agent 1 produced fewer than 3 functional requirements.")

    # every requirement needs a unique id
    ids = [
        item.get("id")
        for group in ("functional_requirements", "non_functional_requirements", "hardware_requirements")
        for item in req[group]
    ]
    if len(ids) != len(set(ids)):
        raise ValueError("Agent 1 produced duplicate requirement ids.")

    # a spec with no acceptance test cannot be verified later
    if not req["acceptance_tests"]:
        raise ValueError("Agent 1 produced no acceptance tests.")
