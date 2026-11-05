
"""
agent1_requirements.py

Agent 1:
Natural-language mission -> structured, testable robot requirements.

Target platform: Arduino Uno R3.
The output is the requirements contract consumed by Agents 2 and 3.
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


def run(
    mission: str,
    catalog: dict[str, Any],
    llm: LLMClient,
    out_path: Path,
) -> dict[str, Any]:
    """
    Generate and validate the requirements specification.
    """

    if not isinstance(mission, str) or not mission.strip():
        raise ValueError("Agent 1 received an empty mission statement.")

    if not isinstance(catalog, dict):
        raise ValueError("Agent 1 requires a valid hardware catalog.")

    board = catalog.get("board", {})
    board_name = board.get("name", "")

    if "uno" not in str(board_name).lower():
        raise ValueError(
            "Agent 1 is configured for Arduino Uno R3, but the "
            f"hardware catalog identifies {board_name!r}."
        )

    result = llm.complete_json(
        system=prompts.A1_SYSTEM,
        user=prompts.a1_user(mission, catalog),
        mock_key="requirements",
    )

    _validate_shape(result, catalog)

    result["_meta"] = {
        "agent": "agent1_requirements",
        "target_board": board_name,
        "model_mode": llm.mode,
        "model": llm.model if llm.mode != "mock" else "golden-example",
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "source_mission_chars": len(mission),
        "status": "validated",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result


def _validate_shape(
    req: dict[str, Any],
    catalog: dict[str, Any] | None = None,
) -> None:
    """
    Validate the Agent 1 output contract.

    This checks structure and hardware consistency. It does not
    determine whether the physical hardware is wired correctly.
    """

    if not isinstance(req, dict):
        raise ValueError("Agent 1 output must be a JSON object.")

    missing = [key for key in REQUIRED_KEYS if key not in req]

    if missing:
        raise ValueError(
            f"Agent 1 output is missing required keys: {missing}"
        )

    list_fields = (
        "functional_requirements",
        "non_functional_requirements",
        "hardware_requirements",
        "interfaces",
        "acceptance_tests",
        "assumptions",
        "open_questions",
    )

    for field in list_fields:
        if not isinstance(req[field], list):
            raise ValueError(
                f"Agent 1 field {field!r} must be a list."
            )

    if len(req["functional_requirements"]) < 3:
        raise ValueError(
            "Agent 1 produced fewer than 3 functional requirements."
        )

    if len(req["non_functional_requirements"]) < 1:
        raise ValueError(
            "Agent 1 produced no non-functional requirements."
        )

    if not req["acceptance_tests"]:
        raise ValueError(
            "Agent 1 produced no acceptance tests."
        )

    # Validate unique requirement IDs.
    requirement_groups = (
        "functional_requirements",
        "non_functional_requirements",
        "hardware_requirements",
    )

    ids: list[str] = []

    for group in requirement_groups:
        for item in req[group]:
            if not isinstance(item, dict):
                raise ValueError(
                    f"An item in {group!r} is not a JSON object."
                )

            item_id = item.get("id")

            if not isinstance(item_id, str) or not item_id.strip():
                raise ValueError(
                    f"An item in {group!r} has no valid ID."
                )

            ids.append(item_id)

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Agent 1 produced duplicate requirement IDs."
        )

    # Every acceptance test must be verifiable.
    for test in req["acceptance_tests"]:
        if not isinstance(test, dict):
            raise ValueError(
                "An acceptance test must be a JSON object."
            )

        for key in ("id", "given", "when", "then"):
            if not test.get(key):
                raise ValueError(
                    f"Acceptance test is missing {key!r}: {test}"
                )

    # Confirm that the requested hardware is in the catalog.
    if catalog is not None:
        available_parts = {
            str(item.get("part", "")).strip().lower()
            for item in catalog.get("parts", [])
            if isinstance(item, dict)
        }

        for item in req["hardware_requirements"]:
            part = str(item.get("part", "")).strip().lower()

            if part and part not in available_parts:
                raise ValueError(
                    "Agent 1 requested hardware that is not in "
                    f"hardware_catalog.json: {item.get('part')!r}"
                )
