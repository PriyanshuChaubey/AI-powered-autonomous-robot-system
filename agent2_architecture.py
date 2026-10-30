"""
agent2_architecture.py - Agent 2 of the firmware pipeline.

    requirements (Agent 1)  ->  architecture + validated ESP32 pin map

This is the stage the panel will care about most. Agent 2 is allowed to
propose a pin assignment, but it is NOT allowed to decide whether that
assignment is legal. validators.check_pin_map() decides.

If the model produces an illegal map, we do one repair round: the error list
is fed back to the model and it must return a corrected map. If it still
fails, the pipeline halts. It never silently ships bad wiring.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import prompts
import validators
from llm import LLMClient

REQUIRED_KEYS = (
    "board",
    "components",
    "pin_map",
    "power",
    "state_machine",
    "timing",
    "constants",
    "modules",
    "safety",
)

MAX_REPAIR_ROUNDS = 1


def run(
    req: dict[str, Any],
    catalog: dict[str, Any],
    llm: LLMClient,
    out_path: Path,
    check_report_path: Path | None = None,
) -> dict[str, Any]:
    require_ok(req)

    attempt = 0
    history: list[list[dict[str, str]]] = []
    arch: dict[str, Any] = {}

    while attempt <= MAX_REPAIR_ROUNDS:
        arch = llm.complete_json(
            system=prompts.A2_SYSTEM,
            user=prompts.a2_user(req, catalog),
            mock_key="architecture",
        )

        _validate_shape(arch)
        issues = validators.check_pin_map(arch, catalog)
        history.append(issues)

        blocking = validators.errors(issues)
        if not blocking:
            break

        # Repack only the errors so the model gets a short, actionable message.
        detail = "\n".join(f"- {i['rule']}: {i['message']}" for i in blocking)
        req = dict(req)
        req["_pin_map_errors"] = detail
        attempt += 1

        if attempt > MAX_REPAIR_ROUNDS:
            report = validators.format_report(issues)
            _write_report(check_report_path, arch, history)
            raise ValueError(
                "Agent 2 could not produce a legal pin map after "
                f"{MAX_REPAIR_ROUNDS} repair round(s):\n{report}"
            )

    arch["_meta"] = {
        "agent": "agent2_architecture",
        "model_mode": llm.mode,
        "model": llm.model if llm.mode != "mock" else "golden-example",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repair_rounds": attempt,
        "pin_map_status": "validated",
        "errors": 0,
        "warnings": len(validators.warnings(history[-1])),
    }
    arch["_pin_checks"] = history[-1]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(arch, indent=2), encoding="utf-8")
    _write_report(check_report_path, arch, history)
    return arch


def require_ok(req: dict[str, Any]) -> None:
    if "_meta" not in req:
        raise ValueError("Agent 1 output was not produced by the pipeline (missing _meta).")


def _validate_shape(arch: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in arch]
    if missing:
        raise ValueError(f"Agent 2 output is missing keys: {missing}")


def _write_report(path: Path | None, arch: dict[str, Any], history: list[list[dict[str, str]]]) -> None:
    if path is None:
        return
    lines = [
        "PIN MAP VALIDATION REPORT",
        "=" * 40,
        "",
        f"Board: {arch.get('board', '?')}",
        f"Repair rounds used: {len(history) - 1}",
        "",
    ]
    for n, issues in enumerate(history, start=1):
        lines.append(f"Round {n}: {len(validators.errors(issues))} error(s), "
                     f"{len(validators.warnings(issues))} warning(s)")
    lines.append("")
    lines.append("Final result:")
    lines.append(validators.format_report(history[-1]))
    lines.append("")
    lines.append("Decoded pin map:")
    for e in arch.get("pin_map", []):
        lines.append(f"  GPIO{e.get('gpio'):>2}  {e.get('signal'):<14} {e.get('direction'):<7} -> {e.get('connected_to')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
