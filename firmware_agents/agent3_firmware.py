
"""
agent3_firmware.py
Agent 3: Arduino Uno R3 Firmware Generator

Responsibilities:
1. Generate Arduino Uno-compatible firmware from validated architecture.
2. Validate the firmware output structure.
3. Run static firmware linting.
4. Attempt one automatic repair if linting fails.
5. Save the Arduino sketch and firmware metadata.
6. Generate a firmware lint report.

Target: Arduino Uno R3 (ATmega328P)
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

ALLOWED_EXTENSIONS = {
    ".ino",
    ".h",
    ".hpp",
    ".c",
    ".cpp",
}


def _validate_architecture(arch: dict[str, Any]) -> None:
    """Check that Agent 2 produced a validated Uno architecture."""

    if not isinstance(arch, dict):
        raise ValueError("Architecture must be a JSON object.")

    metadata = arch.get("_meta", {})

    if metadata.get("pin_map_status") != "validated":
        raise ValueError(
            "Agent 2 architecture is not validated. "
            "Run Agent 2 successfully before Agent 3."
        )

    board = arch.get("board", "")

    if isinstance(board, dict):
        board_name = str(
            board.get("name", board.get("board_name", ""))
        )
    else:
        board_name = str(board)

    if "uno" not in board_name.lower():
        raise ValueError(
            "Agent 3 is configured for Arduino Uno R3. "
            f"Received board: {board_name}"
        )

    if not isinstance(arch.get("pin_map"), list):
        raise ValueError("Architecture must contain a pin_map list.")

    if not arch["pin_map"]:
        raise ValueError("Architecture pin_map cannot be empty.")


def _validate_shape(result: dict[str, Any]) -> None:
    """Validate the structure returned by the firmware generator."""

    if not isinstance(result, dict):
        raise ValueError(
            "Agent 3 must return a JSON object."
        )

    files = result.get("files")

    if not isinstance(files, list) or not files:
        raise ValueError(
            "Agent 3 returned no firmware files."
        )

    source_found = False

    for file_entry in files:
        if not isinstance(file_entry, dict):
            raise ValueError(
                f"Invalid firmware file entry: {file_entry}"
            )

        for key in ("path", "language", "content"):
            if key not in file_entry:
                raise ValueError(
                    f"Firmware file entry is missing {key!r}: "
                    f"{file_entry}"
                )

        file_path = Path(str(file_entry["path"]))

        if file_path.is_absolute() or ".." in file_path.parts:
            raise ValueError(
                f"Unsafe firmware output path: {file_entry['path']}"
            )

        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported firmware file extension: "
                f"{file_path.suffix}"
            )

        if not isinstance(file_entry["content"], str):
            raise ValueError(
                f"Firmware content must be text: {file_entry['path']}"
            )

        if file_path.suffix.lower() in {".ino", ".c", ".cpp"}:
            source_found = True

    if not source_found:
        raise ValueError(
            "Agent 3 did not generate an Arduino source file "
            "(.ino, .c or .cpp)."
        )


def _first_source(result: dict[str, Any]) -> str:
    """Return the primary Arduino/C++ source file."""

    files = result.get("files", [])

    # Prefer the Arduino sketch.
    for file_entry in files:
        if str(file_entry.get("path", "")).lower().endswith(".ino"):
            return str(file_entry.get("content", ""))

    # Otherwise use a C/C++ source file.
    for file_entry in files:
        if str(file_entry.get("path", "")).lower().endswith(
            (".c", ".cpp")
        ):
            return str(file_entry.get("content", ""))

    return ""


def _write_report(
    path: Path | None,
    history: list[list[dict[str, str]]],
    arch: dict[str, Any],
) -> None:
    """Generate a readable firmware lint report."""

    if path is None or not history:
        return

    lines = [
        "ARDUINO UNO R3 - FIRMWARE LINT REPORT",
        "=" * 55,
        "",
        "TARGET BOARD: Arduino Uno R3 (ATmega328P)",
        "",
        "VALIDATION HISTORY",
        "-" * 55,
    ]

    for round_number, issues in enumerate(history, start=1):
        errors = validators.errors(issues)
        warnings = validators.warnings(issues)

        lines.append(
            f"Round {round_number}: "
            f"{len(errors)} error(s), "
            f"{len(warnings)} warning(s)"
        )

    lines.extend([
        "",
        "FINAL LINT RESULT",
        "-" * 55,
        validators.format_report(history[-1]),
        "",
        "ARCHITECTURE PIN MAP",
        "-" * 55,
    ])

    for entry in arch.get("pin_map", []):
        if not isinstance(entry, dict):
            lines.append(f"Invalid pin-map entry: {entry}")
            continue

        signal = entry.get(
            "signal",
            entry.get("component", "Unknown"),
        )

        pin = entry.get(
            "pin",
            entry.get("gpio", "Not specified"),
        )

        lines.append(f"{signal}: Arduino Uno pin {pin}")

    lines.extend([
        "",
        "HARDWARE SAFETY REMINDERS",
        "-" * 55,
        "- Verify all wiring before connecting power.",
        "- Do not power the MG995 servo from the Uno 5V pin.",
        "- Use a separate regulated servo supply rated for its current.",
        "- Use an appropriate external supply for the DC motors.",
        "- Connect the Uno, motor driver and servo supply grounds.",
        "- Test with the robot wheels lifted before floor testing.",
        "- Verify emergency-stop and obstacle-stop behaviour.",
        "- Compile the sketch in Arduino IDE before uploading.",
    ])

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_firmware_files(
    result: dict[str, Any],
    out_dir: Path,
) -> list[str]:
    """Write generated firmware files inside the output directory."""

    out_dir.mkdir(parents=True, exist_ok=True)

    written_files = []

    for file_entry in result["files"]:
        relative_path = Path(file_entry["path"])

        # Prevent writing outside the firmware output directory.
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(
                f"Unsafe firmware path rejected: {relative_path}"
            )

        if relative_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {relative_path}"
            )

        target = out_dir / relative_path

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            file_entry["content"],
            encoding="utf-8",
        )

        written_files.append(
            str(relative_path)
        )

    return written_files


def run(
    arch: dict[str, Any],
    llm: LLMClient,
    out_dir: Path,
    lint_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    Execute Agent 3.

    Args:
        arch: Validated architecture produced by Agent 2.
        llm: LLMClient instance.
        out_dir: Directory where firmware files will be saved.
        lint_report_path: Optional firmware lint report path.

    Returns:
        Firmware result dictionary.
    """

    out_dir = Path(out_dir)

    if lint_report_path is not None:
        lint_report_path = Path(lint_report_path)

    _validate_architecture(arch)

    print("\n[Agent 3] Generating Arduino Uno R3 firmware...")

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

        source_code = _first_source(result)

        if not source_code.strip():
            raise ValueError(
                "Generated Arduino source code is empty."
            )

        # Run the existing firmware validator.
        issues = validators.lint_firmware(
            source_code,
            arch,
        )

        history.append(issues)

        blocking_errors = validators.errors(issues)

        if not blocking_errors:
            print("[Agent 3] Firmware lint passed.")
            break

        print("[Agent 3] Firmware lint detected errors.")

        if attempt < MAX_REPAIR_ROUNDS:
            print("[Agent 3] Requesting one firmware repair...")

            error_details = "\n".join(
                f"- {item['rule']}: {item['message']}"
                for item in blocking_errors
            )

            # Pass lint errors to the firmware-generation prompt.
            arch = dict(arch)

            arch["_firmware_lint_errors"] = error_details

            attempt += 1

        else:
            _write_report(
                lint_report_path,
                history,
                arch,
            )

            raise ValueError(
                "Agent 3 firmware failed lint after "
                f"{MAX_REPAIR_ROUNDS} repair round(s):\n"
                + validators.format_report(issues)
            )

    # Save generated firmware files.
    written_files = _write_firmware_files(
        result,
        out_dir,
    )

    # Add generation and validation metadata.
    result["_meta"] = {
        "agent": "agent3_firmware",
        "target_board": "Arduino Uno R3",
        "model_mode": getattr(llm, "mode", "unknown"),
        "model": (
            getattr(llm, "model", "unknown")
            if getattr(llm, "mode", "unknown") != "mock"
            else "golden-example"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),
        "repair_rounds": attempt,
        "files_written": written_files,
        "lint_status": "passed",
        "warnings": len(
            validators.warnings(history[-1])
        ),
    }

    result["_lint_checks"] = history[-1]

    # Save the complete firmware JSON.
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    firmware_json_path = out_dir / "firmware.json"

    firmware_json_path.write_text(
        json.dumps(result, indent=4),
        encoding="utf-8",
    )

    # Save the lint report.
    _write_report(
        lint_report_path,
        history,
        arch,
    )

    print("[Agent 3] Firmware generated successfully.")
    print("[Agent 3] Target: Arduino Uno R3")
    print("[Agent 3] Firmware lint: PASSED")
    print(f"[Agent 3] Files saved in: {out_dir}")
    print(f"[Agent 3] Firmware metadata: {firmware_json_path}")

    if lint_report_path:
        print(f"[Agent 3] Lint report: {lint_report_path}")

    return result


if __name__ == "__main__":
    print(
        "Agent 3 is designed to run through pipeline.py. "
        "Use the pipeline entry point."
    )
