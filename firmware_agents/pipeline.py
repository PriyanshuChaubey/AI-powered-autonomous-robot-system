
#!/usr/bin/env python3
"""
pipeline.py - Run the first three firmware agents in order.

Target hardware:
    Arduino Uno R3 (ATmega328P)

Usage:
    python pipeline.py
    python pipeline.py --mock
    python pipeline.py path/to/mission.txt
    python pipeline.py path/to/mission.txt --mock

For OpenAI mode:
    FIRM_LLM_MODE=openai FIRM_LLM_API_KEY=your-api-key python pipeline.py

Generated artifacts:
    artifacts/
        1_requirements.json
        2_architecture.json
        pin_map_report.txt
        firmware.json
        robot_controller/
            robot_controller.ino
        firmware_lint_report.txt
        run_log.json

Exit code:
    0 = All three agents completed successfully.
    1 = A pipeline validation or generation stage failed.
    2 = Invalid input or missing mission file.
"""

from __future__ import annotations

import argparse
import json
import sys

from datetime import datetime, timezone
from pathlib import Path

import agent1_requirements
import agent2_architecture
import agent3_firmware

from llm import LLMClient, LLMError


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

HERE = Path(__file__).resolve().parent

DEFAULT_MISSION = HERE / "examples" / "mission.txt"

TARGET_BOARD = "Arduino Uno R3 (ATmega328P)"

DEFAULT_BAUD_RATE = 115200


# ---------------------------------------------------------
# FILE HANDLING
# ---------------------------------------------------------

def load_catalog() -> dict:
    """Load the hardware catalog."""

    catalog_path = HERE / "hardware_catalog.json"

    if not catalog_path.exists():
        raise FileNotFoundError(
            f"Hardware catalog not found: {catalog_path}"
        )

    return json.loads(
        catalog_path.read_text(encoding="utf-8")
    )


def write_log(out: Path, log: dict) -> None:
    """Save pipeline execution log."""

    out.mkdir(parents=True, exist_ok=True)

    log_path = out / "run_log.json"

    log_path.write_text(
        json.dumps(log, indent=4),
        encoding="utf-8",
    )


def count_warnings(arch: dict) -> int:
    """Count architecture warnings without counting errors."""

    checks = arch.get("_pin_checks", [])

    if isinstance(checks, list):
        return sum(
            1
            for item in checks
            if isinstance(item, dict)
            and item.get("level") == "warning"
        )

    return int(
        arch.get("_meta", {}).get("warnings", 0)
    )


def get_repair_rounds(arch: dict) -> int:
    """Read architecture repair count safely."""

    metadata = arch.get("_meta", {})

    if not isinstance(metadata, dict):
        return 0

    return int(metadata.get("repair_rounds", 0))


# ---------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Run the three-agent Arduino Uno firmware pipeline."
        )
    )

    parser.add_argument(
        "mission_file",
        nargs="?",
        type=Path,
        help="Path to the mission description file.",
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "artifacts",
        help="Output directory for generated artifacts.",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock mode.",
    )

    args = parser.parse_args()

    # -----------------------------------------------------
    # LOAD MISSION
    # -----------------------------------------------------

    mission_path = args.mission_file or DEFAULT_MISSION

    if not mission_path.is_absolute():
        mission_path = HERE / mission_path

    if not mission_path.exists():

        print(
            f"[FATAL] Mission file not found: {mission_path}",
            file=sys.stderr,
        )

        print(
            "Pass a valid mission file or create examples/mission.txt.",
            file=sys.stderr,
        )

        return 2

    mission = mission_path.read_text(
        encoding="utf-8"
    ).strip()

    if not mission:

        print(
            f"[FATAL] Mission file is empty: {mission_path}",
            file=sys.stderr,
        )

        return 2

    # -----------------------------------------------------
    # INITIALIZE LLM
    # -----------------------------------------------------

    try:
        llm = LLMClient.from_env()

        if args.mock:
            llm.mode = "mock"

    except Exception as exc:

        print(
            f"[FATAL] Could not initialize LLM: {exc}",
            file=sys.stderr,
        )

        return 2

    # -----------------------------------------------------
    # LOAD HARDWARE CATALOG
    # -----------------------------------------------------

    try:
        catalog = load_catalog()

    except Exception as exc:

        print(
            f"[FATAL] Could not load hardware catalog: {exc}",
            file=sys.stderr,
        )

        return 2

    # -----------------------------------------------------
    # OUTPUT DIRECTORY
    # -----------------------------------------------------

    out = args.out

    if not out.is_absolute():
        out = HERE / out

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    started = datetime.now(timezone.utc)

    log = {
        "started_at": started.isoformat(
            timespec="seconds"
        ),
        "mode": llm.mode,
        "target_board": TARGET_BOARD,
        "mission_file": str(mission_path),
        "stages": [],
    }

    # -----------------------------------------------------
    # PIPELINE HEADER
    # -----------------------------------------------------

    print("=" * 62)
    print(" MULTI-AGENT FIRMWARE GENERATION PIPELINE")
    print(" Agents 1-3")
    print("=" * 62)

    print(f" Mode         : {llm.mode}")
    print(f" Target board : {TARGET_BOARD}")
    print(f" Mission      : {mission_path.name}")
    print("=" * 62)

    try:

        # =================================================
        # AGENT 1: REQUIREMENTS ANALYSIS
        # =================================================

        print(
            "\n[1/3] Requirements analysis ...",
            end=" ",
            flush=True,
        )

        req = agent1_requirements.run(
            mission,
            catalog,
            llm,
            out / "1_requirements.json",
        )

        functional_count = len(
            req.get("functional_requirements", [])
        )

        non_functional_count = len(
            req.get("non_functional_requirements", [])
        )

        acceptance_count = len(
            req.get("acceptance_tests", [])
        )

        print(
            f"OK ({functional_count} FR, "
            f"{non_functional_count} NFR, "
            f"{acceptance_count} tests)"
        )

        log["stages"].append({
            "agent": 1,
            "name": "Requirements Analysis",
            "status": "ok",
            "functional_requirements": functional_count,
            "non_functional_requirements": non_functional_count,
            "acceptance_tests": acceptance_count,
        })

        # =================================================
        # AGENT 2: HARDWARE ARCHITECTURE
        # =================================================

        print(
            "[2/3] Architecture + pin map ...",
            end=" ",
            flush=True,
        )

        arch = agent2_architecture.run(
            req,
            catalog,
            llm,
            out / "2_architecture.json",
            check_report_path=out / "pin_map_report.txt",
        )

        pin_count = len(
            arch.get("pin_map", [])
        )

        warning_count = count_warnings(arch)

        repair_rounds = get_repair_rounds(arch)

        print(
            f"OK ({pin_count} signals, "
            f"{warning_count} warning(s), "
            f"{repair_rounds} repair round(s))"
        )

        log["stages"].append({
            "agent": 2,
            "name": "Hardware Architecture",
            "status": "ok",
            "target_board": TARGET_BOARD,
            "pin_assignments": pin_count,
            "warnings": warning_count,
            "repair_rounds": repair_rounds,
        })

        # =================================================
        # AGENT 3: FIRMWARE GENERATION
        # =================================================

        print(
            "[3/3] Firmware generation + lint ...",
            end=" ",
            flush=True,
        )

        fw = agent3_firmware.run(
            arch,
            llm,
            out,
            lint_report_path=out / "firmware_lint_report.txt",
        )

        firmware_file_count = len(
            fw.get("files", [])
        )

        firmware_warnings = fw.get(
            "_meta", {}
        ).get("warnings", 0)

        print(
            f"OK ({firmware_file_count} file(s), "
            f"{firmware_warnings} warning(s))"
        )

        log["stages"].append({
            "agent": 3,
            "name": "Firmware Generation",
            "status": "ok",
            "firmware_files": firmware_file_count,
            "warnings": firmware_warnings,
            "lint_status": fw.get(
                "_meta", {}
            ).get("lint_status", "unknown"),
        })

    # -----------------------------------------------------
    # PIPELINE ERROR HANDLING
    # -----------------------------------------------------

    except (ValueError, LLMError, FileNotFoundError) as exc:

        log["status"] = "failed"
        log["error"] = str(exc)

        log["duration_s"] = round(
            (
                datetime.now(timezone.utc) - started
            ).total_seconds(),
            2,
        )

        write_log(out, log)

        print("\n")
        print("[BLOCKED]")
        print(str(exc))

        print(
            "\nPipeline stopped. Check the generated reports in:"
        )

        print(out)

        return 1

    except Exception as exc:

        log["status"] = "failed"
        log["error"] = str(exc)
        log["error_type"] = type(exc).__name__

        log["duration_s"] = round(
            (
                datetime.now(timezone.utc) - started
            ).total_seconds(),
            2,
        )

        write_log(out, log)

        print("\n")
        print("[UNEXPECTED ERROR]")
        print(f"{type(exc).__name__}: {exc}")

        print("\nPipeline stopped. Check:")
        print(out)

        raise

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    finished = datetime.now(timezone.utc)

    log["status"] = "ok"

    log["finished_at"] = finished.isoformat(
        timespec="seconds"
    )

    log["duration_s"] = round(
        (finished - started).total_seconds(),
        2,
    )

    write_log(out, log)

    # -----------------------------------------------------
    # OUTPUT SUMMARY
    # -----------------------------------------------------

    sketch = (
        out
        / "robot_controller"
        / "robot_controller.ino"
    )

    print("\n" + "-" * 62)
    print(" PIPELINE COMPLETED SUCCESSFULLY")
    print("-" * 62)

    print(f" Target board  : {TARGET_BOARD}")
    print(f" Requirements  : {out / '1_requirements.json'}")
    print(f" Architecture  : {out / '2_architecture.json'}")
    print(f" Pin report    : {out / 'pin_map_report.txt'}")
    print(f" Firmware JSON : {out / 'firmware.json'}")
    print(f" Arduino sketch: {sketch}")
    print(f" Lint report   : {out / 'firmware_lint_report.txt'}")
    print(f" Execution log : {out / 'run_log.json'}")
    print(f" Duration      : {log['duration_s']} seconds")

    print("-" * 62)

    # -----------------------------------------------------
    # ARDUINO UNO UPLOAD INSTRUCTIONS
    # -----------------------------------------------------

    print("\n NEXT STEPS")
    print("-" * 62)

    print("1. Open the generated .ino file in Arduino IDE.")
    print("2. Select Tools > Board > Arduino AVR Boards > Arduino Uno.")
    print("3. Select the correct COM port.")
    print("4. Verify the sketch before uploading.")
    print("5. Open Serial Monitor at 115200 baud.")
    print("6. Test with the robot wheels lifted before floor testing.")

    print("\n HARDWARE SAFETY")
    print("-" * 62)

    print("- Verify all connections against the pin map report.")
    print("- Use a separate suitable supply for the MG995 servo.")
    print("- Use an external motor supply matched to motor ratings.")
    print("- Connect all system grounds together.")
    print("- Do not run motors until wiring and power are verified.")

    print("\n" + "=" * 62)

    return 0


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
