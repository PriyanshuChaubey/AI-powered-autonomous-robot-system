"""
agent3_firmware.py - Agent 3 of the firmware pipeline.

    validated architecture  ->  Arduino-ESP32 firmware

The generated sketch is not trusted until lint_firmware() agrees that:
  * every pin constant it defines exists in the approved pin map
  * there is no blocking delay() in the loop
  * the scaffold (setup/loop/Serial.begin) is present
  * the safety behaviour the architecture promised actually exists

Failures go back to the model once. A second failure stops the build.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import prompts
import validators
from llm import LLMClient

MAX_REPAIR_ROUNDS = 1


def run(
    arch: dict[str, Any],
    llm: LLMClient,
    out_dir: Path,
    lint_report_path: Path | None = None,
) -> dict[str, Any]:
    attempt = 0
    history: list[list[dict[str, str]]] = []
    result: dict[str, Any] = {}

    while attempt <= MAX_REPAIR_ROUNDS:
        result = llm.complete_json(
            system=prompts.A3_SYSTEM,
            user=prompts.a3_user(arch),
            mock_key="firmware",
        )
        _validate_shape(result)

        code = _first_source(result)
        issues = validators.lint_firmware(code, arch)
        history.append(issues)

        blocking = validators.errors(issues)
        if not blocking:
            break

        detail = "\n".join(f"- {i['rule']}: {i['message']}" for i in blocking)
        arch = dict(arch)
        arch["_firmware_lint_errors"] = detail
        attempt += 1

        if attempt > MAX_REPAIR_ROUNDS:
            _write_report(lint_report_path, history, arch)
            raise ValueError(
                "Agent 3 firmware failed lint after "
                f"{MAX_REPAIR_ROUNDS} repair round(s):\n"
                + validators.format_report(issues)
            )

    # ---- write the sketch to disk
    written: list[str] = []
    for f in result["files"]:
        target = out_dir / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"], encoding="utf-8")
        written.append(str(target.relative_to(out_dir)))

    result["_meta"] = {
        "agent": "agent3_firmware",
        "model_mode": llm.mode,
        "model": llm.model if llm.mode != "mock" else "golden-example",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repair_rounds": attempt,
        "files_written": written,
        "lint_status": "passed",
        "warnings": len(validators.warnings(history[-1])),
    }
    result["_lint_checks"] = history[-1]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "firmware.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_report(lint_report_path, history, arch)
    return result


def _first_source(result: dict[str, Any]) -> str:
    files = result.get("files") or []
    for f in files:
        if str(f.get("path", "")).endswith((".ino", ".c", ".cpp")):
            return str(f.get("content", ""))
    return ""


def _validate_shape(result: dict[str, Any]) -> None:
    if not result.get("files"):
        raise ValueError("Agent 3 returned no files.")
    for f in result["files"]:
        for key in ("path", "language", "content"):
            if key not in f:
                raise ValueError(f"Agent 3 file entry missing {key!r}: {f}")


def _write_report(path: Path | None, history: list[list[dict[str, str]]], arch: dict[str, Any]) -> None:
    if path is None:
        return
    lines = ["FIRMWARE LINT REPORT", "=" * 40, ""]
    for n, issues in enumerate(history, start=1):
        lines.append(
            f"Round {n}: {len(validators.errors(issues))} error(s), "
            f"{len(validators.warnings(issues))} warning(s)"
        )
    lines.append("")
    lines.append("Final result:")
    lines.append(validators.format_report(history[-1]))
    lines.append("")
    lines.append("Cross-checked against pin map:")
    for e in arch.get("pin_map", []):
        lines.append(f"  {e.get('signal'):<14} GPIO{e.get('gpio')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
