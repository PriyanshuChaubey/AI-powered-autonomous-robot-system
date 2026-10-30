#!/usr/bin/env python3
"""
pipeline.py - run the first three agents in order.

    python pipeline.py                      # runs examples/mission.txt in mock mode
    python pipeline.py path/to/mission.txt
    FIRM_LLM_MODE=openai FIRM_LLM_API_KEY=sk-... python pipeline.py

Artifacts land in ./artifacts/:
    artifacts/1_requirements.json
    artifacts/2_architecture.json
    artifacts/pin_map_report.txt
    artifacts/robot_controller/robot_controller.ino
    artifacts/firmware_lint_report.txt
    artifacts/run_log.json

Exit code is 0 only if both validator stages passed. That is deliberate: the
pipeline is a gate, not a suggestion.
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

HERE = Path(__file__).resolve().parent
DEFAULT_MISSION = HERE / "examples" / "mission.txt"


def load_catalog() -> dict:
    return json.loads((HERE / "hardware_catalog.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 3-agent firmware pipeline.")
    parser.add_argument("mission_file", nargs="?", type=Path)
    parser.add_argument("--out", type=Path, default=HERE / "artifacts")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="force mock mode even if FIRM_LLM_MODE is set",
    )
    args = parser.parse_args()

    mission_path = args.mission_file or DEFAULT_MISSION
    if not mission_path.exists():
        print(f"[fatal] mission file not found: {mission_path}", file=sys.stderr)
        print("        pass a path, or create examples/mission.txt", file=sys.stderr)
        return 2

    mission = mission_path.read_text(encoding="utf-8").strip()
    if not mission:
        print(f"[fatal] mission file is empty: {mission_path}", file=sys.stderr)
        return 2

    llm = LLMClient.from_env()
    if args.mock:
        llm.mode = "mock"

    catalog = load_catalog()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    log = {
        "started_at": started.isoformat(timespec="seconds"),
        "mode": llm.mode,
        "mission_file": str(mission_path),
        "stages": [],
    }

    print("=" * 62)
    print(" FIRMWARE PIPELINE - agents 1-3")
    print(f" mode: {llm.mode}   mission: {mission_path.name}")
    print("=" * 62)

    try:
        # ---------------- Agent 1
        print("\n[1/3] Requirements ...", end=" ", flush=True)
        req = agent1_requirements.run(
            mission, catalog, llm, out / "1_requirements.json"
        )
        print(
            f"ok  ({len(req['functional_requirements'])} FR, "
            f"{len(req['non_functional_requirements'])} NFR, "
            f"{len(req['acceptance_tests'])} tests)"
        )
        log["stages"].append({"agent": 1, "status": "ok"})

        # ---------------- Agent 2
        print("[2/3] Architecture + pin map ...", end=" ", flush=True)
        arch = agent2_architecture.run(
            req,
            catalog,
            llm,
            out / "2_architecture.json",
            check_report_path=out / "pin_map_report.txt",
        )
        warn = len(arch.get("_pin_checks", [])) - sum(
            1 for i in arch.get("_pin_checks", []) if i["level"] == "error"
        )
        print(
            f"ok  ({len(arch['pin_map'])} signals, "
            f"{warn} warning(s), {arch['_meta']['repair_rounds']} repair round(s))"
        )
        log["stages"].append({"agent": 2, "status": "ok", "warnings": warn})

        # ---------------- Agent 3
        print("[3/3] Firmware generation + lint ...", end=" ", flush=True)
        fw = agent3_firmware.run(
            arch,
            llm,
            out,
            lint_report_path=out / "firmware_lint_report.txt",
        )
        print(
            f"ok  ({len(fw['files'])} file(s), "
            f"{fw['_meta']['warnings']} warning(s))"
        )
        log["stages"].append({"agent": 3, "status": "ok"})

    except (ValueError, LLMError) as exc:
        log["status"] = "failed"
        log["error"] = str(exc)
        _write_log(out, log)
        print(f"\n\n[BLOCKED] {exc}\n")
        print("Nothing was accepted. See the report files in", out)
        return 1

    log["status"] = "ok"
    log["duration_s"] = round((datetime.now(timezone.utc) - started).total_seconds(), 2)
    _write_log(out, log)

    sketch = out / "robot_controller" / "robot_controller.ino"
    print("\n" + "-" * 62)
    print(" DONE")
    print(f"   requirements : {out / '1_requirements.json'}")
    print(f"   architecture : {out / '2_architecture.json'}")
    print(f"   pin report   : {out / 'pin_map_report.txt'}")
    print(f"   firmware     : {sketch}")
    print(f"   lint report  : {out / 'firmware_lint_report.txt'}")
    print(f"   duration     : {log['duration_s']}s")
    print("-" * 62)
    print(" Next: open the .ino in Arduino IDE, select 'ESP32 Dev Module',")
    print("       flash it, then open the serial monitor at 115200 baud.")
    return 0


def _write_log(out: Path, log: dict) -> None:
    (out / "run_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
