"""
validators.py - the contract checks that sit between the agents.

This module is the honest core of the project. A language model will happily
emit `#define TRIG 5` or wire two devices to the same pin. These functions catch
that before the code reaches the board.

Two checks:
  check_pin_map(arch, catalog)      -> validates Agent 2's pin assignment
  lint_firmware(code, pin_map)      -> validates that Agent 3's code actually
                                       uses the pins Agent 2 approved, and
                                       follows the timing rules it promised

Every problem is a dict: {"level": "error"|"warning", "rule": ..., "message": ...}
An "error" must block the stage; a "warning" is reported in the review.
"""

from __future__ import annotations

import re
from typing import Any

# --------------------------------------------------------------------------
# ESP32 hardware facts. These live in hardware_catalog.json too, so the rules
# can be edited without touching this file.
# --------------------------------------------------------------------------
FORBIDDEN_GPIO = {6, 7, 8, 9, 10, 11}       # internal SPI flash
INPUT_ONLY_GPIO = {34, 35, 36, 39}          # no output driver
STRAPPING_GPIO = {0, 2, 5, 12, 15}          # boot-mode pins
UART0_GPIO = {1, 3}                         # USB serial
VALID_GPIO = set(range(0, 40)) - {20, 24, 28, 29, 30, 31}  # not broken out on most devkits


def _issue(level: str, rule: str, message: str) -> dict[str, str]:
    return {"level": level, "rule": rule, "message": message}


# --------------------------------------------------------------------------
# Check 1 - the pin map
# --------------------------------------------------------------------------
def check_pin_map(arch: dict[str, Any], catalog: dict[str, Any] | None = None) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    pin_map = arch.get("pin_map") or []
    if not pin_map:
        return [_issue("error", "pin_map.missing", "Architecture contains no pin_map.")]

    seen: dict[int, str] = {}
    for entry in pin_map:
        signal = str(entry.get("signal", "?"))
        pin = entry.get("gpio")
        direction = str(entry.get("direction", "")).lower()

        # -- type / range
        if not isinstance(pin, int):
            issues.append(
                _issue("error", "pin.type", f"{signal}: gpio must be an integer, got {pin!r}.")
            )
            continue
        if pin not in VALID_GPIO:
            issues.append(
                _issue("error", "pin.range", f"{signal}: GPIO{pin} is not available on this devkit.")
            )
            continue

        # -- reserved for the flash chip
        if pin in FORBIDDEN_GPIO:
            issues.append(
                _issue(
                    "error",
                    "pin.flash",
                    f"{signal}: GPIO{pin} is wired to the SPI flash. Using it crashes the board.",
                )
            )

        # -- input-only pins used as outputs
        if pin in INPUT_ONLY_GPIO and direction == "output":
            issues.append(
                _issue(
                    "error",
                    "pin.input_only",
                    f"{signal}: GPIO{pin} is input-only and cannot drive an output.",
                )
            )

        # -- boot strapping
        if pin in STRAPPING_GPIO and direction == "output":
            issues.append(
                _issue(
                    "warning",
                    "pin.strapping",
                    f"{signal}: GPIO{pin} is a boot-strapping pin; confirm it is not held HIGH at power-on.",
                )
            )

        # -- serial
        if pin in UART0_GPIO:
            issues.append(
                _issue(
                    "warning",
                    "pin.uart0",
                    f"{signal}: GPIO{pin} is the USB serial line; telemetry may break.",
                )
            )

        # -- double booking
        if pin in seen and seen[pin] != signal:
            issues.append(
                _issue(
                    "error",
                    "pin.duplicate",
                    f"GPIO{pin} is assigned to both {seen[pin]} and {signal}.",
                )
            )
        seen[pin] = signal

        # -- modules that need an explicit direction
        if direction not in {"input", "output", "analog", "pwm"}:
            issues.append(
                _issue("warning", "pin.direction", f"{signal}: unclear direction {direction!r}.")
            )

    issues.extend(_check_power(arch))
    return issues


def _check_power(arch: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    power = arch.get("power") or {}
    servos = [
        c
        for c in arch.get("components", [])
        if "servo" in str(c.get("part", "")).lower()
    ]
    if servos and not power.get("servo_supply"):
        issues.append(
            _issue(
                "warning",
                "power.servo",
                "A servo is present but no separate 5 V servo supply is declared; "
                "powering it from the board regulator can brown out the ESP32.",
            )
        )
    if not power.get("motor_supply"):
        issues.append(
            _issue("warning", "power.motor", "No motor supply declared; motors draw amps, not milliamps.")
        )
    return issues


# --------------------------------------------------------------------------
# Check 2 - the generated firmware
# --------------------------------------------------------------------------
PIN_DEFINE = re.compile(
    r"^\s*#define\s+(?P<name>[A-Z][A-Z0-9_]*)\s+(?P<pin>\d+)\b", re.MULTILINE
)


def extract_pin_defines(code: str) -> dict[str, int]:
    """Every `#define NAME 12` in the sketch, as {NAME: 12}."""
    return {m.group("name"): int(m.group("pin")) for m in PIN_DEFINE.finditer(code)}


def lint_firmware(code: str, arch: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    approved = {
        str(e["signal"]): int(e["gpio"])
        for e in arch.get("pin_map", [])
        if isinstance(e.get("gpio"), int)
    }

    if not code.strip():
        return [_issue("error", "code.empty", "Firmware output is empty.")]

    defines = extract_pin_defines(code)
    if not defines:
        issues.append(
            _issue("error", "code.no_defines", "No #define pin constants found; cannot verify the wiring.")
        )

    # 1. every pin literal in the code must be an approved pin
    approved_values = set(approved.values())
    for name, pin in defines.items():
        if pin not in approved_values:
            issues.append(
                _issue(
                    "error",
                    "code.unapproved_pin",
                    f"{name} is set to GPIO{pin}, which is not in the approved pin map "
                    f"{sorted(approved_values)}.",
                )
            )

    # 2. every approved signal should appear in the code
    for signal, pin in approved.items():
        if pin not in defines.values():
            issues.append(
                _issue(
                    "warning",
                    "code.unused_signal",
                    f"{signal} (GPIO{pin}) is in the architecture but never defined in the firmware.",
                )
            )

    # 3. banned calls
    if re.search(r"\bdelay\s*\(", code):
        issues.append(
            _issue(
                "error",
                "code.blocking_delay",
                "delay() is used. A blocking delay stalls the control loop; use millis() timing.",
            )
        )
    if re.search(r"\bpulseIn\s*\(", code):
        issues.append(
            _issue(
                "error",
                "code.blocking_pulsein",
                "pulseIn() blocks for the whole echo timeout. Use a non-blocking echo state machine.",
            )
        )
    if not re.search(r"\bmillis\s*\(", code):
        issues.append(
            _issue("warning", "code.no_millis", "No millis() found; the loop may not be non-blocking.")
        )

    # 4. required scaffolding
    if "Serial.begin" not in code:
        issues.append(
            _issue("error", "code.no_serial", "Serial is never initialised, so there is no telemetry.")
        )
    for func in ("setup", "loop"):
        if not re.search(rf"\bvoid\s+{func}\s*\(", code):
            issues.append(_issue("error", "code.scaffold", f"Missing the {func}() function."))

    # 5. safety behaviour the architecture promised
    #    Matches any function containing "stop" - motorsStop(), stopAll(), etc.
    safety = str(arch.get("safety", "")).lower()
    if "stop" in safety and not re.search(r"\w*stop\w*\s*\(", code, re.IGNORECASE):
        issues.append(
            _issue("warning", "code.no_stop", "Architecture promises a stop behaviour; no stop routine found.")
        )

    return issues


# --------------------------------------------------------------------------
# Reporting helpers
# --------------------------------------------------------------------------
def errors(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    return [i for i in issues if i["level"] == "error"]


def warnings(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    return [i for i in issues if i["level"] == "warning"]


def format_report(issues: list[dict[str, str]]) -> str:
    if not issues:
        return "  OK - no issues"
    marks = {"error": "ERROR", "warning": "WARN "}
    return "\n".join(
        f"  [{marks.get(i['level'], i['level'])}] {i['rule']}: {i['message']}" for i in issues
    )
