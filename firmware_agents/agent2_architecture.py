
"""
Agent 2: Hardware Architecture Designer
Target board: Arduino Uno R3 (ATmega328P)

Responsibilities:
1. Convert validated requirements into a hardware architecture.
2. Generate the component list and GPIO pin map.
3. Define power requirements, state machine, timing and constants.
4. Validate pin assignments against hardware_catalog.json.
5. Attempt one LLM repair if validation fails.
6. Save architecture.json and pin_map_report.txt.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import prompts
import validators


REQUIRED_KEYS = [
    "board",
    "components",
    "pin_map",
    "power",
    "state_machine",
    "timing",
    "constants",
    "modules",
    "safety",
]


def _load_json(path: Path) -> Dict[str, Any]:
    """Load a JSON file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_json(data: Dict[str, Any], path: Path) -> None:
    """Save JSON with readable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)



def _validate_input_requirements(req: Dict[str, Any]) -> None:
    """Validate requirements received from Agent 1."""

    if not isinstance(req, dict):
        raise ValueError("Requirements must be a JSON object.")

    # Support the field names used by different Agent 1 versions.
    functional = req.get(
        "functional_requirements",
        req.get("requirements", [])
    )

    non_functional = req.get(
        "non_functional_requirements",
        req.get("non_functional", [])
    )

    hardware = req.get(
        "hardware_requirements",
        req.get("hardware", [])
    )

    acceptance = req.get(
        "acceptance_criteria",
        req.get("acceptance_tests", req.get("tests", []))
    )

    missing = []

    if not isinstance(functional, list) or not functional:
        missing.append("functional_requirements")

    if not isinstance(non_functional, list) or not non_functional:
        missing.append("non_functional_requirements")

    if not isinstance(hardware, list) or not hardware:
        missing.append("hardware_requirements")

    if not isinstance(acceptance, list) or not acceptance:
        missing.append("acceptance_criteria")

    if missing:
        raise ValueError(
            f"Agent 1 requirements are missing valid data: {missing}"
        )

    metadata = req.get("_meta", {})

    if not isinstance(metadata, dict):
        metadata = {}

    if metadata.get("status") != "validated":
        raise ValueError(
            "Agent 1 requirements are not validated. "
            "Check agent1_requirements.py."
        )

    board = str(
        req.get(
            "target_board",
            metadata.get("target_board", "Arduino Uno R3")
        )
    )

    if "uno" not in board.lower():
        raise ValueError(
            f"Expected Arduino Uno R3. Received: {board}"
        )



def _validate_catalog(catalog: Dict[str, Any]) -> None:
    """Ensure the hardware catalog targets Arduino Uno."""

    if not isinstance(catalog, dict):
        raise ValueError("Hardware catalog must be a JSON object.")

    board = catalog.get("board", {})

    if isinstance(board, dict):
        board_name = str(
            board.get("name", board.get("board_name", ""))
        )
    else:
        board_name = str(board)

    if "uno" not in board_name.lower():
        raise ValueError(
            "hardware_catalog.json must specify Arduino Uno R3."
        )


def _validate_architecture_shape(
    arch: Dict[str, Any]
) -> List[str]:
    """Validate the basic architecture structure."""

    errors = []

    if not isinstance(arch, dict):
        return ["Architecture output must be a JSON object."]

    for key in REQUIRED_KEYS:
        if key not in arch:
            errors.append(f"Missing required architecture field: {key}")

    if errors:
        return errors

    board = arch.get("board")

    if isinstance(board, dict):
        board_name = str(
            board.get("name", board.get("board_name", ""))
        )
    else:
        board_name = str(board)

    if "uno" not in board_name.lower():
        errors.append(
            "Target board must be Arduino Uno R3, not ESP32 or another board."
        )

    for field in [
        "components",
        "pin_map",
        "state_machine",
        "timing",
        "constants",
        "modules",
        "safety",
    ]:
        if not isinstance(arch.get(field), (list, dict, str)):
            errors.append(
                f"Invalid data type for architecture field: {field}"
            )

    if not isinstance(arch.get("pin_map"), list):
        errors.append("pin_map must be a list of pin assignment objects.")

    elif not arch["pin_map"]:
        errors.append("pin_map cannot be empty.")

    return errors


def _write_report(
    arch: Dict[str, Any],
    validation_errors: List[str],
    report_path: Path,
) -> None:
    """Write a human-readable architecture validation report."""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "ARDUINO UNO R3 - HARDWARE ARCHITECTURE VALIDATION",
        "=" * 55,
        "",
        f"Target board: {arch.get('board', 'Not specified')}",
        "",
        "PIN ASSIGNMENTS",
        "-" * 55,
    ]

    for item in arch.get("pin_map", []):
        if not isinstance(item, dict):
            lines.append(f"Invalid pin entry: {item}")
            continue

        component = item.get(
            "component",
            item.get("name", "Unknown component"),
        )

        signal = item.get(
            "signal",
            item.get("function", "Not specified"),
        )

        pin = item.get(
            "pin",
            item.get("gpio", "Not specified"),
        )

        mode = item.get(
            "mode",
            item.get("type", "Not specified"),
        )

        lines.append(
            f"{component} | {signal} | Pin: {pin} | Mode: {mode}"
        )

    lines.extend([
        "",
        "VALIDATION RESULT",
        "-" * 55,
    ])

    if validation_errors:
        lines.append("STATUS: FAILED")
        lines.append("")

        for error in validation_errors:
            lines.append(f"- {error}")
    else:
        lines.append("STATUS: PASSED")
        lines.append(
            "Arduino Uno pin assignments passed architecture validation."
        )

    lines.extend([
        "",
        "IMPORTANT HARDWARE NOTES",
        "-" * 55,
        "- Arduino Uno R3 is the primary controller.",
        "- Use analogWrite() only on supported PWM pins for motor speed.",
        "- MG995 servo signal can use a digital pin with the Servo library.",
        "- Do not power the MG995 directly from the Uno 5V pin.",
        "- Use an appropriate external motor supply for the L298N.",
        "- Connect all grounds together.",
        "- Do not assume encoders, IMU or IR sensors are installed.",
        "- Verify actual wiring and power ratings before running motors.",
    ])

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _get_validation_errors(
    arch: Dict[str, Any],
    catalog: Dict[str, Any],
) -> List[str]:
    """Run structural and hardware pin-map validation."""

    errors = _validate_architecture_shape(arch)

    if errors:
        return errors

    try:
        result = validators.check_pin_map(arch, catalog)

        # Support validators that return either a boolean or a list.
        if isinstance(result, list):
            errors.extend(str(item) for item in result)

        elif isinstance(result, tuple):
            if len(result) >= 2:
                status, details = result[0], result[1]

                if not status:
                    if isinstance(details, list):
                        errors.extend(str(item) for item in details)
                    else:
                        errors.append(str(details))

        elif result is False:
            errors.append("Pin-map validation failed.")

    except Exception as exc:
        errors.append(f"Pin-map validator error: {exc}")

    return errors


def run(
    req: Dict[str, Any],
    catalog: Dict[str, Any],
    llm: Any,
    out_path: str,
    check_report_path: str = None,
) -> Dict[str, Any]:
    """
    Execute Agent 2.

    Args:
        req: Validated requirements from Agent 1.
        catalog: Hardware catalog JSON.
        llm: LLMClient instance.
        out_path: Output path for architecture JSON.
        check_report_path: Optional pin-map validation report path.

    Returns:
        Validated architecture dictionary.
    """

    output_path = Path(out_path)

    if check_report_path:
        report_path = Path(check_report_path)
    else:
        report_path = output_path.parent / "pin_map_report.txt"

    _validate_input_requirements(req)
    _validate_catalog(catalog)

    print("\n[Agent 2] Designing Arduino Uno R3 architecture...")

    architecture = llm.complete_json(
        system=prompts.A2_SYSTEM,
        user=prompts.a2_user(req, catalog),
        mock_key="architecture",
    )

    if not isinstance(architecture, dict):
        raise ValueError(
            "Agent 2 did not return a valid architecture JSON object."
        )

    # First validation attempt.
    errors = _get_validation_errors(architecture, catalog)

    # One automatic repair attempt.
    if errors:
        print("[Agent 2] Architecture validation failed.")
        print("[Agent 2] Requesting one repair attempt...")

        architecture["_pin_map_errors"] = errors

        repaired = llm.complete_json(
            system=prompts.A2_SYSTEM,
            user=prompts.a2_user(req, catalog),
            mock_key="architecture",
        )

        if isinstance(repaired, dict):
            architecture = repaired

        errors = _get_validation_errors(architecture, catalog)

    # Stop if the architecture still fails validation.
    if errors:
        _write_report(
            architecture,
            errors,
            report_path,
        )

        _save_json(
            architecture,
            output_path,
        )

        raise ValueError(
            "Agent 2 architecture validation failed after one repair attempt. "
            f"Check report: {report_path}"
        )

    # Add validation metadata.
    architecture["_meta"] = {
    "agent": "agent2_architecture",
    "target_board": "Arduino Uno R3",
    "pin_map_status": "validated",
    "status": "validated",
    "repair_rounds": 0,
    }

    _save_json(
        architecture,
        output_path,
    )

    _write_report(
        architecture,
        [],
        report_path,
    )

    print("[Agent 2] Architecture generated successfully.")
    print("[Agent 2] Arduino Uno pin map validated.")
    print(f"[Agent 2] Architecture saved: {output_path}")
    print(f"[Agent 2] Validation report saved: {report_path}")

    return architecture


if __name__ == "__main__":
    print(
        "Agent 2 is designed to run through pipeline.py. "
        "Use the pipeline entry point."
    )
