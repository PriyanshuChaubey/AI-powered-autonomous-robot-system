#!/usr/bin/env python3
"""
demo_validator_fail.py - the demo that proves the project is not "just an LLM".

It takes the golden architecture, makes three realistic mistakes a language
model actually makes, and shows the validator catching each one:

  1. SONAR_TRIG moved to GPIO 5   -> boot strapping pin + it is also a
                                     plausible-sounding "free" pin
  2. IR_LEFT moved to GPIO 4 and IR_RIGHT to GPIO 4 -> two devices on one pin
  3. MOTOR_A_ENA moved to GPIO 6  -> wired to the SPI flash, board would crash

Then it takes the golden firmware and breaks it with delay(500) to show the
code-level lint catching a blocking loop.

Run:  python demo_validator_fail.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import validators
from mock_data import MOCKS

HERE = Path(__file__).resolve().parent


def banner(text: str) -> None:
    print("\n" + "=" * 66)
    print(f" {text}")
    print("=" * 66)


def show(issues: list[dict[str, str]]) -> None:
    for i in issues:
        tag = "BLOCKS BUILD" if i["level"] == "error" else "warning"
        print(f"  [{tag:^12}] {i['rule']}")
        print(f"                 {i['message']}")


def main() -> int:
    catalog = json.loads((HERE / "hardware_catalog.json").read_text(encoding="utf-8"))
    base = MOCKS["architecture"]

    banner("CONTROL - the golden architecture")
    issues = validators.check_pin_map(base, catalog)
    show(issues)
    print(f"\n  result: {len(validators.errors(issues))} error(s) -> "
          f"{'ACCEPTED' if not validators.errors(issues) else 'BLOCKED'}")

    # ---------------------------------------------------------------- case 1
    banner("MISTAKE 1 - the model drives the motors from GPIO 36 (input-only)")
    bad = copy.deepcopy(base)
    for e in bad["pin_map"]:
        if e["signal"] == "MOTOR_A_IN1":
            e["gpio"] = 36
    issues = validators.check_pin_map(bad, catalog)
    show(issues)
    print(f"\n  result: {len(validators.errors(issues))} error(s) -> "
          f"{'ACCEPTED' if not validators.errors(issues) else 'BLOCKED'}")

    # ---------------------------------------------------------------- case 2
    banner("MISTAKE 2 - two sensor signals land on the same GPIO 4")
    bad = copy.deepcopy(base)
    for e in bad["pin_map"]:
        if e["signal"] in {"IR_LEFT", "IR_RIGHT"}:
            e["gpio"] = 4
    issues = validators.check_pin_map(bad, catalog)
    show(issues)
    print(f"\n  result: {len(validators.errors(issues))} error(s) -> "
          f"{'ACCEPTED' if not validators.errors(issues) else 'BLOCKED'}")

    # ---------------------------------------------------------------- case 3
    banner("MISTAKE 3 - the model uses GPIO 6 (wired to the SPI flash)")
    bad = copy.deepcopy(base)
    for e in bad["pin_map"]:
        if e["signal"] == "MOTOR_A_ENA":
            e["gpio"] = 6
    issues = validators.check_pin_map(bad, catalog)
    show(issues)
    print(f"\n  result: {len(validators.errors(issues))} error(s) -> "
          f"{'ACCEPTED' if not validators.errors(issues) else 'BLOCKED'}")

    # ---------------------------------------------------------------- case 3b
    banner("MISTAKE 3b - TRIG on GPIO 5: a warning, not a block")
    print("  GPIO5 is a boot-strapping pin. It is often usable, so this is")
    print("  raised for the engineer to confirm rather than rejected outright.")
    bad = copy.deepcopy(base)
    for e in bad["pin_map"]:
        if e["signal"] == "SONAR_TRIG":
            e["gpio"] = 5
    issues = validators.check_pin_map(bad, catalog)
    show(issues)
    print(f"\n  result: {len(validators.errors(issues))} error(s) -> "
          f"{'ACCEPTED' if not validators.errors(issues) else 'BLOCKED'}")

    # ---------------------------------------------------------------- case 4
    banner("MISTAKE 4 - the firmware uses delay(500) inside loop()")
    code = MOCKS["firmware"]["files"][0]["content"]
    broken = code.replace(
        "  telemetry();\n  statusService(now);",
        "  delay(500);\n  telemetry();\n  statusService(now);",
    )
    issues = validators.lint_firmware(broken, base)
    show(issues)
    print(f"\n  result: {len(validators.errors(issues))} error(s) -> "
          f"{'ACCEPTED' if not validators.errors(issues) else 'BLOCKED'}")

    banner("SUMMARY")
    print("  The model proposes. The validator disposes.")
    print("  Every stage refuses to pass its output on until the checks are green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
