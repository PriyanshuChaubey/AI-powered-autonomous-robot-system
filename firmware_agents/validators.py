
"""
validators.py
Validation layer for the multi-agent robot firmware pipeline.

Target board: Arduino Uno R3 (ATmega328P)

Responsibilities:
1. Validate Agent 2's hardware pin map against hardware_catalog.json.
2. Check power declarations for motors and servos.
3. Validate Agent 3's firmware pin definitions against the approved pin map.
4. Check firmware structure and basic safety requirements.

Issue format:
{"level": "error" | "warning", "rule": "...", "message": "..."}
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _issue(level: str, rule: str, message: str) -> dict[str, str]:
    return {
        "level": level,
        "rule": rule,
        "message": message,
    }


def _get_catalog_constraints(
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Read board constraints from hardware_catalog.json.

    Falls back to Arduino Uno R3 defaults if no catalog is supplied.
    """

    if catalog:
        constraints = catalog.get("constraints", {})
        if constraints:
            return constraints

    return {
        "valid_gpio": list(range(2, 14)),
        "pwm_gpio": [3, 5, 6, 9, 10, 11],
        "reserved_gpio": [0, 1],
        "input_only_gpio": [],
        "forbidden_gpio": [],
        "analog_pins": ["A0", "A1", "A2", "A3", "A4", "A5"],
    }


def _as_int_set(value: Any) -> set[int]:
    """Convert a list of integer pin numbers into a set safely."""

    if not isinstance(value, (list, tuple, set)):
        return set()

    result = set()

    for item in value:
        # bool is a subclass of int, so explicitly exclude it.
        if isinstance(item, int) and not isinstance(item, bool):
            result.add(item)

    return result


# ---------------------------------------------------------------------
# Check 1: Hardware pin-map validation
# ---------------------------------------------------------------------

def check_pin_map(
    arch: dict[str, Any],
    catalog: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """
    Validate Agent 2's proposed pin map.

    Expected pin-map entry:
    {
        "signal": "MOTOR_LEFT_EN",
        "gpio": 5,
        "direction": "pwm",
        "connected_to": "L298N ENA"
    }

    Supported directions:
    input, output, analog, pwm
    """

    issues: list[dict[str, str]] = []

    pin_map = arch.get("pin_map") or []

    if not isinstance(pin_map, list) or not pin_map:
        return [
            _issue(
                "error",
                "pin_map.missing",
                "Architecture contains no valid pin_map.",
            )
        ]

    constraints = _get_catalog_constraints(catalog)

    valid_gpio = _as_int_set(constraints.get("valid_gpio", []))
    pwm_gpio = _as_int_set(constraints.get("pwm_gpio", []))
    reserved_gpio = _as_int_set(constraints.get("reserved_gpio", []))
    input_only_gpio = _as_int_set(
        constraints.get("input_only_gpio", [])
    )
    forbidden_gpio = _as_int_set(
        constraints.get("forbidden_gpio", [])
    )

    reserved_reason = constraints.get(
        "reserved_reason",
        "This pin is reserved by the hardware configuration.",
    )

    forbidden_reason = constraints.get(
        "forbidden_reason",
        "This pin is unavailable on the selected board.",
    )

    input_only_reason = constraints.get(
        "input_only_reason",
        "This pin cannot be used as an output.",
    )

    seen: dict[int, str] = {}

    for index, entry in enumerate(pin_map):

        if not isinstance(entry, dict):
            issues.append(
                _issue(
                    "error",
                    "pin.entry",
                    f"Pin-map entry {index} must be a JSON object.",
                )
            )
            continue

        signal = str(entry.get("signal", "?")).strip()
        pin = entry.get("gpio")
        direction = str(
            entry.get("direction", "")
        ).strip().lower()

        # ---------------------------------------------------------
        # 1. Validate pin number type
        # ---------------------------------------------------------

        if not isinstance(pin, int) or isinstance(pin, bool):
            issues.append(
                _issue(
                    "error",
                    "pin.type",
                    f"{signal}: gpio must be an integer pin number, "
                    f"got {pin!r}.",
                )
            )
            continue

        # ---------------------------------------------------------
        # 2. Validate pin availability
        # ---------------------------------------------------------

        if pin not in valid_gpio:
            issues.append(
                _issue(
                    "error",
                    "pin.range",
                    f"{signal}: GPIO{pin} is not listed as an "
                    "available pin in hardware_catalog.json.",
                )
            )
            continue

        # ---------------------------------------------------------
        # 3. Check forbidden pins
        # ---------------------------------------------------------

        if pin in forbidden_gpio:
            issues.append(
                _issue(
                    "error",
                    "pin.forbidden",
                    f"{signal}: GPIO{pin} cannot be used. "
                    f"{forbidden_reason}",
                )
            )

        # ---------------------------------------------------------
        # 4. Check reserved pins
        # ---------------------------------------------------------

        if pin in reserved_gpio:
            issues.append(
                _issue(
                    "error",
                    "pin.reserved",
                    f"{signal}: GPIO{pin} is reserved. "
                    f"{reserved_reason}",
                )
            )

        # ---------------------------------------------------------
        # 5. Check input-only pins
        # ---------------------------------------------------------

        if pin in input_only_gpio and direction in {
            "output",
            "pwm",
        }:
            issues.append(
                _issue(
                    "error",
                    "pin.input_only",
                    f"{signal}: GPIO{pin} cannot be used as an "
                    f"output. {input_only_reason}",
                )
            )

        # ---------------------------------------------------------
        # 6. Check PWM compatibility
        # ---------------------------------------------------------

        if direction == "pwm" and pin not in pwm_gpio:
            issues.append(
                _issue(
                    "error",
                    "pin.pwm",
                    f"{signal}: GPIO{pin} does not support PWM "
                    "according to hardware_catalog.json. "
                    f"Available PWM pins: {sorted(pwm_gpio)}.",
                )
            )

        # ---------------------------------------------------------
        # 7. Validate direction
        # ---------------------------------------------------------

        allowed_directions = {
            "input",
            "output",
            "analog",
            "pwm",
        }

        if direction not in allowed_directions:
            issues.append(
                _issue(
                    "error",
                    "pin.direction",
                    f"{signal}: unsupported direction {direction!r}. "
                    f"Use one of {sorted(allowed_directions)}.",
                )
            )

        # ---------------------------------------------------------
        # 8. Detect duplicate pin assignments
        # ---------------------------------------------------------

        if pin in seen and seen[pin] != signal:
            issues.append(
                _issue(
                    "error",
                    "pin.duplicate",
                    f"GPIO{pin} is assigned to both "
                    f"{seen[pin]} and {signal}.",
                )
            )
        else:
            seen[pin] = signal

        # ---------------------------------------------------------
        # 9. Check missing signal names
        # ---------------------------------------------------------

        if not signal or signal == "?":
            issues.append(
                _issue(
                    "error",
                    "pin.signal_missing",
                    f"Pin-map entry {index} has no valid signal name.",
                )
            )

        # ---------------------------------------------------------
        # 10. Check missing connection description
        # ---------------------------------------------------------

        if not entry.get("connected_to"):
            issues.append(
                _issue(
                    "warning",
                    "pin.connection_missing",
                    f"{signal}: connected_to is missing. "
                    "Add the hardware component or terminal name.",
                )
            )

    # Power checks are independent of individual pin assignments.
    issues.extend(_check_power(arch))

    return issues


# ---------------------------------------------------------------------
# Check 2: Power validation
# ---------------------------------------------------------------------

def _check_power(
    arch: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Check whether the architecture declares appropriate power supplies.

    This checks declarations only. It does not electrically verify
    the actual battery, regulator, wiring, or current capacity.
    """

    issues: list[dict[str, str]] = []

    power = arch.get("power") or {}
    components = arch.get("components") or []

    if not isinstance(power, dict):
        return [
            _issue(
                "error",
                "power.format",
                "The architecture power field must be a JSON object.",
            )
        ]

    component_names = []

    for component in components:
        if not isinstance(component, dict):
            continue

        name = str(component.get("part", ""))
        component_names.append(name.lower())

    has_servo = any(
        "servo" in name
        for name in component_names
    )

    has_motor = any(
        "motor" in name
        for name in component_names
    ) or any(
        keyword in name
        for name in component_names
        for keyword in ("chassis", "l298", "dc gear")
    )

    # Servo power
    if has_servo and not power.get("servo_supply"):
        issues.append(
            _issue(
                "warning",
                "power.servo",
                "A servo is present, but no separate servo supply "
                "is declared. The MG995 should use a suitable "
                "regulated 5V-6V supply with adequate current "
                "capacity, not the Arduino Uno 5V pin.",
            )
        )

    # Motor power
    if has_motor and not power.get("motor_supply"):
        issues.append(
            _issue(
                "warning",
                "power.motor",
                "Motors are present, but no external motor supply "
                "is declared. Use a supply matched to the motor "
                "ratings and connect the grounds together.",
            )
        )

    # Common ground
    if (
        (has_servo or has_motor)
        and power.get("common_ground_required") is False
    ):
        issues.append(
            _issue(
                "error",
                "power.common_ground",
                "The architecture disables common ground. The "
                "Arduino, motor driver, and external servo supply "
                "must share a common ground.",
            )
        )

    return issues


# ---------------------------------------------------------------------
# Check 3: Firmware pin definitions
# ---------------------------------------------------------------------

PIN_DEFINE = re.compile(
    r"^\s*#define\s+"
    r"(?P<name>[A-Z][A-Z0-9_]*)\s+"
    r"(?P<pin>\d+)\b",
    re.MULTILINE,
)


def extract_pin_defines(code: str) -> dict[str, int]:
    """
    Extract numeric #define declarations.

    Example:
        #define MOTOR_LEFT_EN 5

    Returns:
        {"MOTOR_LEFT_EN": 5}
    """

    return {
        match.group("name"): int(match.group("pin"))
        for match in PIN_DEFINE.finditer(code)
    }


def _looks_like_pin_name(name: str) -> bool:
    """
    Identify macros that are likely to represent hardware pins.

    This avoids incorrectly treating numeric constants such as
    PWM_FREQ or STOP_DISTANCE_CM as GPIO assignments.
    """

    keywords = (
        "PIN",
        "MOTOR",
        "ENA",
        "ENB",
        "IN1",
        "IN2",
        "IN3",
        "IN4",
        "TRIG",
        "ECHO",
        "SONAR",
        "SERVO",
        "LED",
        "IR_",
        "SENSOR",
    )

    return any(keyword in name for keyword in keywords)


# ---------------------------------------------------------------------
# Check 4: Firmware linting
# ---------------------------------------------------------------------

def lint_firmware(
    code: str,
    arch: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Validate generated Arduino firmware against Agent 2's architecture.

    Checks:
    - Firmware is not empty.
    - Pin definitions match approved architecture pins.
    - Approved pins are represented in firmware.
    - Blocking delay() and pulseIn() calls are flagged.
    - millis() timing is present.
    - Serial.begin(), setup(), and loop() exist.
    - A stop routine exists when promised by the architecture.
    """

    issues: list[dict[str, str]] = []

    if not isinstance(code, str) or not code.strip():
        return [
            _issue(
                "error",
                "code.empty",
                "Firmware output is empty.",
            )
        ]

    pin_map = arch.get("pin_map") or []

    approved: dict[str, int] = {}

    for entry in pin_map:
        if not isinstance(entry, dict):
            continue

        signal = str(entry.get("signal", "")).strip()
        gpio = entry.get("gpio")

        if (
            signal
            and isinstance(gpio, int)
            and not isinstance(gpio, bool)
        ):
            approved[signal] = gpio

    if not approved:
        issues.append(
            _issue(
                "error",
                "code.no_approved_pins",
                "Architecture contains no valid approved GPIO assignments.",
            )
        )

    defines = extract_pin_defines(code)

    if not defines:
        issues.append(
            _issue(
                "error",
                "code.no_defines",
                "No numeric #define declarations found. "
                "Cannot verify the firmware pin assignments.",
            )
        )

    approved_values = set(approved.values())

    # -------------------------------------------------------------
    # 1. Validate pin-like macros against approved pins
    # -------------------------------------------------------------

    firmware_pin_values: set[int] = set()

    for name, pin in defines.items():

        if not _looks_like_pin_name(name):
            continue

        firmware_pin_values.add(pin)

        if pin not in approved_values:
            issues.append(
                _issue(
                    "error",
                    "code.unapproved_pin",
                    f"{name} is assigned GPIO{pin}, which is not "
                    f"in the approved architecture pin map "
                    f"{sorted(approved_values)}.",
                )
            )

    # -------------------------------------------------------------
    # 2. Check that approved pins are represented in firmware
    # -------------------------------------------------------------

    for signal, pin in approved.items():

        if pin not in firmware_pin_values:
            issues.append(
                _issue(
                    "warning",
                    "code.unused_signal",
                    f"{signal} (GPIO{pin}) is in the architecture "
                    "but no matching pin-like #define was found "
                    "in the firmware.",
                )
            )

    # -------------------------------------------------------------
    # 3. Check blocking delay()
    # -------------------------------------------------------------

    if re.search(r"\bdelay\s*\(", code):
        issues.append(
            _issue(
                "error",
                "code.blocking_delay",
                "delay() is used. Blocking delays can stall the "
                "robot control loop. Prefer millis()-based timing. "
                "Short pulse-generation delays may need a separate "
                "hardware-specific review.",
            )
        )

    # -------------------------------------------------------------
    # 4. Check blocking pulseIn()
    # -------------------------------------------------------------

    if re.search(r"\bpulseIn\s*\(", code):
        issues.append(
            _issue(
                "warning",
                "code.blocking_pulsein",
                "pulseIn() waits synchronously for an ultrasonic "
                "echo. Consider a timeout-controlled or "
                "non-blocking echo measurement approach.",
            )
        )

    # -------------------------------------------------------------
    # 5. Check millis() timing
    # -------------------------------------------------------------

    if not re.search(r"\bmillis\s*\(", code):
        issues.append(
            _issue(
                "warning",
                "code.no_millis",
                "No millis() call found. Review whether the main "
                "control loop uses non-blocking timing.",
            )
        )

    # -------------------------------------------------------------
    # 6. Check serial initialization
    # -------------------------------------------------------------

    if not re.search(r"\bSerial\s*\.\s*begin\s*\(", code):
        issues.append(
            _issue(
                "error",
                "code.no_serial",
                "Serial.begin() is missing. USB serial communication "
                "and telemetry may not work.",
            )
        )

    # -------------------------------------------------------------
    # 7. Check Arduino program structure
    # -------------------------------------------------------------

    for function_name in ("setup", "loop"):

        pattern = rf"\bvoid\s+{function_name}\s*\("

        if not re.search(pattern, code):
            issues.append(
                _issue(
                    "error",
                    "code.scaffold",
                    f"Missing the Arduino {function_name}() function.",
                )
            )

    # -------------------------------------------------------------
    # 8. Check stop routine
    # -------------------------------------------------------------

    safety = arch.get("safety", "")

    if isinstance(safety, dict):
        safety_text = " ".join(
            str(value)
            for value in safety.values()
        ).lower()
    else:
        safety_text = str(safety).lower()

    if "stop" in safety_text:
        stop_pattern = (
            r"\b\w*stop\w*\s*\("
            r"|\b\w*brake\w*\s*\("
        )

        if not re.search(stop_pattern, code, re.IGNORECASE):
            issues.append(
                _issue(
                    "warning",
                    "code.no_stop",
                    "Architecture promises a stop behaviour, "
                    "but no stop or brake routine was found.",
                )
            )

    return issues


# ---------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------

def errors(
    issues: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Return only blocking errors."""

    return [
        issue
        for issue in issues
        if issue.get("level") == "error"
    ]


def warnings(
    issues: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Return only non-blocking warnings."""

    return [
        issue
        for issue in issues
        if issue.get("level") == "warning"
    ]


def format_report(
    issues: list[dict[str, str]],
) -> str:
    """Format validation issues as a readable report."""

    if not issues:
        return "  OK - no issues"

    marks = {
        "error": "ERROR",
        "warning": "WARN ",
    }

    lines = []

    for issue in issues:
        level = issue.get("level", "unknown")
        rule = issue.get("rule", "unknown")
        message = issue.get("message", "")

        mark = marks.get(level, level.upper())

        lines.append(
            f"  [{mark}] {rule}: {message}"
        )

    return "\n".join(lines)
