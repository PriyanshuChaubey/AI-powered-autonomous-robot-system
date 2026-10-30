"""
mock_data.py - golden outputs used when FIRM_LLM_MODE=mock (the default).

These are not stubs that get thrown away. They are a fixed, known-good example
of what each agent must produce, which lets you:
  * run and demo the whole pipeline with no API key and no network
  * regression-test the validators (the demo_validator_fail.py script mutates
    these on purpose to prove the checks fire)
  * show the panel the exact JSON contract between agents

When you switch to a real model, the same three dicts are produced by the LLM
and must pass the same validators.
"""

from __future__ import annotations

MOCKS: dict[str, dict] = {}

# ===========================================================================
# Agent 1 - requirements
# ===========================================================================
MOCKS["requirements"] = {
    "project": "Obstacle-Avoiding Robot with AI-Generated Firmware",
    "mission": (
        "Build a two-wheeled ESP32 robot that drives forward, measures the distance "
        "to the obstacle ahead with an ultrasonic sensor, and stops and turns before "
        "contact. The control firmware is produced by the project's AI pipeline, not "
        "written by hand."
    ),
    "functional_requirements": [
        {"id": "FR-1", "text": "Drive both wheels forward at a configurable duty cycle."},
        {"id": "FR-2", "text": "Measure the distance ahead using an ultrasonic sensor at a fixed interval."},
        {"id": "FR-3", "text": "Stop the motors when the measured distance is below a safe threshold."},
        {"id": "FR-4", "text": "Turn away from the obstacle, then resume forward motion when the path clears."},
        {"id": "FR-5", "text": "Stream telemetry (state, distance, sensor readings) over serial at 115200 baud."},
        {"id": "FR-6", "text": "Indicate the current state with a status LED (blink while moving, solid while stopped)."},
    ],
    "non_functional_requirements": [
        {"id": "NFR-1", "text": "Control loop must run at approximately 50 Hz without blocking delays."},
        {"id": "NFR-2", "text": "Ultrasonic readings must be spaced at least 60 ms apart for sensor settling."},
        {"id": "NFR-3", "text": "No GPIO may exceed 3.3 V; the 5 V echo line requires a voltage divider."},
        {"id": "NFR-4", "text": "Firmware must build on both ESP32 Arduino core 2.x and 3.x."},
        {"id": "NFR-5", "text": "A single source file, under 300 lines, with named constants for every pin."},
    ],
    "hardware_requirements": [
        {"id": "HR-1", "part": "ESP32-WROOM-32 DevKit v1", "qty": 1, "purpose": "Controller"},
        {"id": "HR-2", "part": "L298N dual H-bridge", "qty": 1, "purpose": "Motor driver"},
        {"id": "HR-3", "part": "HC-SR04 ultrasonic sensor", "qty": 1, "purpose": "Forward distance"},
        {"id": "HR-4", "part": "IR obstacle module", "qty": 2, "purpose": "Left and right edge detection"},
        {"id": "HR-5", "part": "2WD chassis with two gear motors", "qty": 1, "purpose": "Locomotion"},
        {"id": "HR-6", "part": "SG90 servo (optional)", "qty": 1, "purpose": "Sensor scan mount"},
        {"id": "HR-7", "part": "2x 18650 cells + holder", "qty": 1, "purpose": "Power"},
    ],
    "interfaces": [
        {"name": "motor_left", "kind": "pwm + gpio", "signals": ["EN", "IN1", "IN2"]},
        {"name": "motor_right", "kind": "pwm + gpio", "signals": ["EN", "IN3", "IN4"]},
        {"name": "sonar", "kind": "gpio", "signals": ["TRIG", "ECHO"]},
        {"name": "ir_left", "kind": "digital in", "signals": ["OUT"]},
        {"name": "ir_right", "kind": "digital in", "signals": ["OUT"]},
        {"name": "servo", "kind": "pwm", "signals": ["SIG"], "optional": True},
        {"name": "led", "kind": "digital out", "signals": ["ANODE"]},
        {"name": "telemetry", "kind": "uart", "signals": ["TX", "RX"], "baud": 115200},
    ],
    "acceptance_tests": [
        {
            "id": "AT-1",
            "given": "the robot is powered and the path is clear",
            "when": "the loop runs",
            "then": "both motors are driven forward and telemetry reports state=FORWARD",
        },
        {
            "id": "AT-2",
            "given": "an obstacle is placed 20 cm in front",
            "when": "the next distance sample is taken",
            "then": "the motors stop within one control cycle and state=STOPPED",
        },
        {
            "id": "AT-3",
            "given": "the robot is stopped at an obstacle",
            "when": "the turn timer elapses",
            "then": "the robot turns for a fixed duration and returns to FORWARD",
        },
        {
            "id": "AT-4",
            "given": "the serial monitor is open at 115200",
            "when": "the robot runs",
            "then": "one JSON telemetry line is printed per control cycle",
        },
        {
            "id": "AT-5",
            "given": "the code is compiled",
            "when": "built against Arduino core 2.x and 3.x",
            "then": "both builds succeed with no errors",
        },
    ],
    "assumptions": [
        "The HC-SR04 echo line is divided down to 3.3 V before reaching the ESP32.",
        "The L298N is powered from the battery pack, with a common ground to the ESP32.",
        "The IR modules are active-low (output goes LOW when an obstacle is detected).",
        "Only forward, stop and a fixed-duration turn are required; no PID or mapping.",
    ],
    "open_questions": [
        "Should the servo scan be enabled in the first hardware demo or left for phase two?",
        "What minimum obstacle distance is safe for the chassis at full duty cycle?",
    ],
}

# ===========================================================================
# Agent 2 - architecture
# ===========================================================================
MOCKS["architecture"] = {
    "board": "ESP32-WROOM-32 DevKit v1",
    "summary": (
        "One non-blocking control loop at 50 Hz. An L298N drives two DC motors; an "
        "HC-SR04 provides forward distance; two IR modules provide side awareness; a "
        "status LED and a JSON telemetry line expose the internal state. The servo scan "
        "is compiled in but disabled by default."
    ),
    "components": [
        {"ref": "U1", "part": "ESP32-WROOM-32 DevKit v1", "role": "controller"},
        {"ref": "U2", "part": "L298N dual H-bridge", "role": "motor driver"},
        {"ref": "U3", "part": "HC-SR04 ultrasonic sensor", "role": "forward distance"},
        {"ref": "U4", "part": "IR obstacle module (left)", "role": "left edge"},
        {"ref": "U5", "part": "IR obstacle module (right)", "role": "right edge"},
        {"ref": "M1", "part": "DC gear motor (left)", "role": "actuator"},
        {"ref": "M2", "part": "DC gear motor (right)", "role": "actuator"},
        {"ref": "S1", "part": "SG90 servo", "role": "sensor scan", "optional": True},
        {"ref": "D1", "part": "status LED", "role": "state indication"},
    ],
    "pin_map": [
        {"signal": "MOTOR_A_ENA", "gpio": 25, "direction": "pwm", "connected_to": "U2 ENA", "note": "left motor speed"},
        {"signal": "MOTOR_A_IN1", "gpio": 26, "direction": "output", "connected_to": "U2 IN1", "note": ""},
        {"signal": "MOTOR_A_IN2", "gpio": 27, "direction": "output", "connected_to": "U2 IN2", "note": ""},
        {"signal": "MOTOR_B_ENB", "gpio": 14, "direction": "pwm", "connected_to": "U2 ENB", "note": "right motor speed"},
        {"signal": "MOTOR_B_IN3", "gpio": 32, "direction": "output", "connected_to": "U2 IN3", "note": ""},
        {"signal": "MOTOR_B_IN4", "gpio": 33, "direction": "output", "connected_to": "U2 IN4", "note": ""},
        {"signal": "SONAR_TRIG", "gpio": 18, "direction": "output", "connected_to": "U3 TRIG", "note": ""},
        {"signal": "SONAR_ECHO", "gpio": 19, "direction": "input", "connected_to": "U3 ECHO (via 1k/2k divider)", "note": "5 V sensor, divided"},
        {"signal": "IR_LEFT", "gpio": 34, "direction": "input", "connected_to": "U4 OUT", "note": "input-only pin, active-low"},
        {"signal": "IR_RIGHT", "gpio": 35, "direction": "input", "connected_to": "U5 OUT", "note": "input-only pin, active-low"},
        {"signal": "SERVO_SCAN", "gpio": 13, "direction": "pwm", "connected_to": "S1 SIG", "note": "disabled by default"},
        {"signal": "LED_STATUS", "gpio": 2, "direction": "output", "connected_to": "D1 anode", "note": "on-board LED, strapping pin"},
    ],
    "power": {
        "motor_supply": "2x18650 (7.4 V nominal) into L298N VIN; L298N 5 V out feeds the ESP32 VIN",
        "servo_supply": "L298N 5 V rail, with a 470 uF capacitor across the servo terminals",
        "common_ground": True,
        "estimated_current_ma": {"idle": 120, "both_motors": 900, "peak": 1800},
    },
    "state_machine": {
        "initial": "FORWARD",
        "states": [
            {"name": "FORWARD", "entry": "both motors forward at CRUISE_DUTY"},
            {"name": "STOPPED", "entry": "both motors off; brake for TURN_MS"},
            {"name": "TURNING", "entry": "left motor reverse, right motor forward for TURN_MS"},
        ],
        "transitions": [
            {"from": "FORWARD", "to": "STOPPED", "when": "distance_cm < STOP_DISTANCE_CM"},
            {"from": "FORWARD", "to": "TURNING", "when": "IR_LEFT is blocked and IR_RIGHT is clear"},
            {"from": "STOPPED", "to": "TURNING", "when": "TURN_MS has elapsed"},
            {"from": "TURNING", "to": "FORWARD", "when": "TURN_MS has elapsed and the path is clear"},
        ],
    },
    "timing": {
        "loop_hz": 50,
        "loop_period_ms": 20,
        "sonar_period_ms": 60,
        "turn_ms": 450,
        "telemetry_baud": 115200,
    },
    "constants": {
        "STOP_DISTANCE_CM": 20,
        "CLEAR_DISTANCE_CM": 30,
        "CRUISE_DUTY": 180,
        "TURN_DUTY": 200,
        "PWM_FREQ_HZ": 1000,
        "PWM_RESOLUTION_BITS": 8,
    },
    "modules": [
        {"name": "motors", "responsibility": "direction and speed control, forward/stop/turn primitives"},
        {"name": "sonar", "responsibility": "non-blocking HC-SR04 pulse and echo measurement"},
        {"name": "sensing", "responsibility": "IR edge flags"},
        {"name": "control", "responsibility": "the FORWARD/STOPPED/TURNING state machine"},
        {"name": "telemetry", "responsibility": "one JSON line per cycle"},
        {"name": "status", "responsibility": "LED blink pattern per state"},
    ],
    "safety": (
        "stop() is called on every transition into STOPPED and in setup() before the "
        "motors are ever energised. A distance reading of 0 cm or a timeout on the echo "
        "pulse is treated as an obstacle, so a failed sensor fails safe rather than "
        "driving blind."
    ),
}

# ===========================================================================
# Agent 3 - firmware
# ===========================================================================
MOCKS["firmware"] = {
    "files": [
        {
            "path": "robot_controller/robot_controller.ino",
            "language": "cpp",
            "description": "ESP32 obstacle-avoiding robot controller",
            "content": r"""/*
 * robot_controller.ino
 * Obstacle-avoiding two-wheel robot for ESP32-WROOM-32.
 *
 * GENERATED by the project's firmware pipeline (Agent 3). Do not hand-edit:
 * change the architecture JSON and regenerate, so the pin map and the code
 * stay in sync.
 *
 * Wiring is fixed by architecture.json. Every pin below is validated against it.
 */

#include <Arduino.h>

// ---------------------------------------------------------------- pin map
#define MOTOR_A_ENA      25
#define MOTOR_A_IN1      26
#define MOTOR_A_IN2      27
#define MOTOR_B_ENB      14
#define MOTOR_B_IN3      32
#define MOTOR_B_IN4      33

#define SONAR_TRIG       18
#define SONAR_ECHO       19

#define IR_LEFT          34
#define IR_RIGHT         35

#define SERVO_SCAN       13
#define LED_STATUS        2

// -------------------------------------------------------------- constants
static const int   STOP_DISTANCE_CM   = 20;
static const int   CLEAR_DISTANCE_CM  = 30;
static const int   CRUISE_DUTY        = 180;
static const int   TURN_DUTY          = 200;
static const int   PWM_FREQ           = 1000;
static const int   PWM_BITS           = 8;
static const unsigned long LOOP_MS    = 20;    // 50 Hz
static const unsigned long SONAR_MS   = 60;    // sensor settling
static const unsigned long TURN_MS    = 450;
static const unsigned long ECHO_TIMEOUT_US = 25000UL;  // ~4 m round trip

// ------------------------------------------------------- PWM compatibility
// Arduino-ESP32 core 2.x and 3.x use different LEDC APIs. This shim keeps the
// sketch compiling on both (NFR-4).
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  #define PWM_SETUP(pin, ch)            ledcAttach((pin), PWM_FREQ, PWM_BITS)
  #define PWM_WRITE(pin, ch, duty)      ledcWrite((pin), (duty))
#else
  #define PWM_SETUP(pin, ch)            do { ledcSetup((ch), PWM_FREQ, PWM_BITS); ledcAttachPin((pin), (ch)); } while (0)
  #define PWM_WRITE(pin, ch, duty)      ledcWrite((ch), (duty))
#endif

static const int CH_A = 0;
static const int CH_B = 1;

// ------------------------------------------------------------------ state
enum RobotState { FORWARD, STOPPED, TURNING };
static RobotState state = FORWARD;

static unsigned long lastLoopMs    = 0;
static unsigned long lastSonarMs   = 0;
static unsigned long stateSinceMs  = 0;
static int  distanceCm  = -1;          // -1 = no reading yet
static bool leftBlocked  = false;
static bool rightBlocked = false;
static bool ledOn = false;

// ------------------------------------------------------------------ motors
static void motorsStop() {
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN3, LOW);
  digitalWrite(MOTOR_B_IN4, LOW);
  PWM_WRITE(MOTOR_A_ENA, CH_A, 0);
  PWM_WRITE(MOTOR_B_ENB, CH_B, 0);
}

static void motorsForward(int duty) {
  digitalWrite(MOTOR_A_IN1, HIGH);
  digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN3, HIGH);
  digitalWrite(MOTOR_B_IN4, LOW);
  PWM_WRITE(MOTOR_A_ENA, CH_A, duty);
  PWM_WRITE(MOTOR_B_ENB, CH_B, duty);
}

static void motorsTurnRight(int duty) {
  // left wheel back, right wheel forward -> pivot turn
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, HIGH);
  digitalWrite(MOTOR_B_IN3, HIGH);
  digitalWrite(MOTOR_B_IN4, LOW);
  PWM_WRITE(MOTOR_A_ENA, CH_A, duty);
  PWM_WRITE(MOTOR_B_ENB, CH_B, duty);
}

// ------------------------------------------------------------------- sonar
// Fully non-blocking HC-SR04 driver. The ping is started on one cycle and the
// echo is sampled on later cycles, so loop() never stalls (NFR-1). A timeout
// or a zero reading is treated as an obstacle (fail safe).
enum SonarPhase { SONAR_IDLE, SONAR_WAIT_RISE, SONAR_WAIT_FALL };
static SonarPhase sonarPhase = SONAR_IDLE;
static unsigned long sonarEdgeUs = 0;

static void sonarPing() {
  digitalWrite(SONAR_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(SONAR_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(SONAR_TRIG, LOW);
  sonarEdgeUs = micros();
  sonarPhase = SONAR_WAIT_RISE;
}

static void sonarStep() {
  switch (sonarPhase) {
    case SONAR_IDLE:
      break;

    case SONAR_WAIT_RISE:
      if (digitalRead(SONAR_ECHO) == HIGH) {
        sonarEdgeUs = micros();
        sonarPhase = SONAR_WAIT_FALL;
      } else if (micros() - sonarEdgeUs > ECHO_TIMEOUT_US) {
        distanceCm = 0;                  // no echo: fail safe
        sonarPhase = SONAR_IDLE;
      }
      break;

    case SONAR_WAIT_FALL:
      if (digitalRead(SONAR_ECHO) == LOW) {
        unsigned long width = micros() - sonarEdgeUs;
        distanceCm = (int)(width / 58UL);  // us -> cm
        sonarPhase = SONAR_IDLE;
      } else if (micros() - sonarEdgeUs > ECHO_TIMEOUT_US) {
        distanceCm = 0;                  // echo never ended: fail safe
        sonarPhase = SONAR_IDLE;
      }
      break;
  }
}

// --------------------------------------------------------------- telemetry
static void telemetry() {
  Serial.print("{\"state\":\"");
  Serial.print(state == FORWARD ? "FORWARD" : state == STOPPED ? "STOPPED" : "TURNING");
  Serial.print("\",\"distance_cm\":");
  Serial.print(distanceCm);
  Serial.print(",\"ir_left\":");
  Serial.print(leftBlocked ? 1 : 0);
  Serial.print(",\"ir_right\":");
  Serial.print(rightBlocked ? 1 : 0);
  Serial.println("}");
}

// ------------------------------------------------------------------ status
static void statusService(unsigned long now) {
  bool want = (state == FORWARD) ? ((now / 250) % 2 == 0) : true;
  if (want != ledOn) {
    ledOn = want;
    digitalWrite(LED_STATUS, ledOn ? HIGH : LOW);
  }
}

// -------------------------------------------------------------------- setup
void setup() {
  Serial.begin(115200);

  pinMode(MOTOR_A_IN1, OUTPUT);
  pinMode(MOTOR_A_IN2, OUTPUT);
  pinMode(MOTOR_B_IN3, OUTPUT);
  pinMode(MOTOR_B_IN4, OUTPUT);
  PWM_SETUP(MOTOR_A_ENA, CH_A);
  PWM_SETUP(MOTOR_B_ENB, CH_B);

  pinMode(SONAR_TRIG, OUTPUT);
  pinMode(SONAR_ECHO, INPUT);

  pinMode(IR_LEFT, INPUT);
  pinMode(IR_RIGHT, INPUT);

  pinMode(LED_STATUS, OUTPUT);

  motorsStop();               // never energise the motors before this
  state = FORWARD;
  stateSinceMs = millis();
}

// --------------------------------------------------------------------- loop
void loop() {
  unsigned long now = millis();
  if (now - lastLoopMs < LOOP_MS) return;
  lastLoopMs = now;

  // ---- sensors
  sonarStep();                        // advance the echo measurement every cycle
  if (sonarPhase == SONAR_IDLE && now - lastSonarMs >= SONAR_MS) {
    lastSonarMs = now;
    sonarPing();                      // sensor has settled, start the next ping
  }
  leftBlocked  = (digitalRead(IR_LEFT)  == LOW);
  rightBlocked = (digitalRead(IR_RIGHT) == LOW);

  // ---- state machine
  switch (state) {
    case FORWARD:
      if (distanceCm >= 0 && distanceCm < STOP_DISTANCE_CM) {
        motorsStop();
        state = STOPPED;
        stateSinceMs = now;
      } else if (leftBlocked && !rightBlocked) {
        motorsTurnRight(TURN_DUTY);
        state = TURNING;
        stateSinceMs = now;
      } else {
        motorsForward(CRUISE_DUTY);
      }
      break;

    case STOPPED:
      if (now - stateSinceMs >= TURN_MS) {
        motorsTurnRight(TURN_DUTY);
        state = TURNING;
        stateSinceMs = now;
      }
      break;

    case TURNING:
      if (now - stateSinceMs >= TURN_MS) {
        if (distanceCm >= CLEAR_DISTANCE_CM) {
          motorsForward(CRUISE_DUTY);
          state = FORWARD;
        } else {
          motorsStop();
          state = STOPPED;
        }
        stateSinceMs = now;
      }
      break;
  }

  telemetry();
  statusService(now);
}
""",
        }
    ],
    "library_dependencies": [
        {"name": "ESP32 Arduino core", "version": ">=2.0.0", "source": "board manager"}
    ],
    "build_notes": [
        "Board: ESP32 Dev Module. Upload speed 115200.",
        "Enable 'Core Debug Level: None' for a smaller binary.",
        "The servo scan define is present but unused in v1; it is reserved for phase two.",
    ],
    "self_check": [
        "Every #define pin is taken from the validated architecture pin map.",
        "No delay() in the control loop; all timing uses millis()/micros().",
        "The ultrasonic driver is a three-phase non-blocking state machine, so no echo wait stalls loop().",
        "motorsStop() runs in setup() and on every transition into STOPPED.",
        "A failed echo (timeout or never-ending pulse) maps to distance 0, which is treated as an obstacle.",
    ],
}
