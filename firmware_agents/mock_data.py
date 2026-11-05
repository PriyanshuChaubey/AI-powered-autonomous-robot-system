
"""
mock_data.py - Arduino Uno R3 golden outputs for mock mode.

These fixtures provide deterministic outputs for Agents 1, 2 and 3.
They are used by the pipeline when FIRM_LLM_MODE=mock.
"""

from __future__ import annotations

MOCKS: dict[str, dict] = {}


# ===========================================================================
# Agent 1 - Requirements
# ===========================================================================

MOCKS["requirements"] = {
    "project": "Multi-Agent AI-Based Autonomous Path Planning and Obstacle Avoidance Robot",
    "mission": (
        "Build a two-wheeled autonomous robot controlled by an Arduino Uno R3. "
        "The robot uses an HC-SR04 ultrasonic sensor mounted on an MG995 servo "
        "to detect obstacles. An L298N driver controls the two DC motors. "
        "A Python-based multi-agent system generates the hardware architecture "
        "and firmware, while the navigation system plans and replans routes."
    ),
    "functional_requirements": [
        {
            "id": "FR-1",
            "text": "Drive the left and right DC motors independently through the L298N motor driver."
        },
        {
            "id": "FR-2",
            "text": "Measure the distance to obstacles using the HC-SR04 ultrasonic sensor."
        },
        {
            "id": "FR-3",
            "text": "Stop both motors when an obstacle is detected within the configured safety distance."
        },
        {
            "id": "FR-4",
            "text": "Control the MG995 servo to position the ultrasonic sensor for directional scanning."
        },
        {
            "id": "FR-5",
            "text": "Receive movement commands and transmit robot telemetry through USB serial communication."
        },
        {
            "id": "FR-6",
            "text": "Stop the motors when sensor measurements or incoming control commands are invalid."
        },
    ],
    "non_functional_requirements": [
        {
            "id": "NFR-1",
            "text": "The control loop shall use non-blocking millis()-based timing."
        },
        {
            "id": "NFR-2",
            "text": "Ultrasonic measurements shall be separated by at least 60 ms."
        },
        {
            "id": "NFR-3",
            "text": "All controller-connected digital signals shall remain within the Arduino Uno 5 V logic limits."
        },
        {
            "id": "NFR-4",
            "text": "Firmware shall use Arduino AVR-compatible APIs and compile for Arduino Uno R3."
        },
        {
            "id": "NFR-5",
            "text": "The generated firmware shall use only the validated architecture pin map."
        },
    ],
    "hardware_requirements": [
        {
            "id": "HR-1",
            "part": "Arduino Uno R3",
            "qty": 1,
            "purpose": "Primary robot controller."
        },
        {
            "id": "HR-2",
            "part": "L298N dual H-bridge motor driver",
            "qty": 1,
            "purpose": "Independent direction and speed control of two DC motors."
        },
        {
            "id": "HR-3",
            "part": "HC-SR04 ultrasonic distance sensor",
            "qty": 1,
            "purpose": "Obstacle distance measurement."
        },
        {
            "id": "HR-4",
            "part": "MG995 servo motor",
            "qty": 1,
            "purpose": "Directional positioning of the ultrasonic sensor."
        },
        {
            "id": "HR-5",
            "part": "Two-wheel robot chassis with DC gear motors",
            "qty": 1,
            "purpose": "Differential-drive robot platform."
        },
        {
            "id": "HR-6",
            "part": "Solderless breadboard",
            "qty": 1,
            "purpose": "Prototyping and signal connections."
        },
    ],
    "interfaces": [
        {
            "name": "motor_left",
            "kind": "PWM + digital GPIO",
            "signals": ["ENA", "IN1", "IN2"]
        },
        {
            "name": "motor_right",
            "kind": "PWM + digital GPIO",
            "signals": ["ENB", "IN3", "IN4"]
        },
        {
            "name": "ultrasonic_sensor",
            "kind": "digital GPIO",
            "signals": ["TRIG", "ECHO"]
        },
        {
            "name": "servo",
            "kind": "digital servo control",
            "signals": ["SIG"]
        },
        {
            "name": "computer_communication",
            "kind": "USB serial",
            "signals": ["TX", "RX"],
            "baud": 115200
        },
    ],
    "acceptance_tests": [
        {
            "id": "AT-1",
            "given": "the robot is powered and the motor driver is enabled",
            "when": "a forward movement command is received",
            "then": "both motors rotate in the forward direction."
        },
        {
            "id": "AT-2",
            "given": "an obstacle is detected within the configured safety distance",
            "when": "the next valid distance measurement is processed",
            "then": "both motors stop."
        },
        {
            "id": "AT-3",
            "given": "the robot is stationary",
            "when": "a servo scan command is received",
            "then": "the MG995 moves to the requested scan position."
        },
        {
            "id": "AT-4",
            "given": "the robot is connected to the computer over USB",
            "when": "the controller operates",
            "then": "telemetry is transmitted at 115200 baud."
        },
        {
            "id": "AT-5",
            "given": "the ultrasonic sensor returns no valid echo",
            "when": "the measurement timeout occurs",
            "then": "the motors remain stopped or enter the configured fail-safe state."
        },
    ],
    "assumptions": [
        "Arduino Uno R3 is the primary controller.",
        "The MG995 uses a separate regulated 5-6 V supply with adequate current capacity.",
        "The L298N motor supply is selected according to the actual DC motor ratings.",
        "The motor driver, controller and servo supply share a common ground.",
        "The exact battery configuration has not yet been confirmed.",
        "Wheel encoders and an IMU are not currently confirmed, so precise odometry is not assumed.",
        "USB serial is used for the initial computer-to-robot communication."
    ],
    "open_questions": [
        "What are the rated voltage and stall current of the DC gear motors?",
        "What battery and regulator configuration will be used?",
        "What scan angles should be used for left, front and right obstacle measurements?",
        "What movement command protocol should the Python navigation system use?",
    ],
}


# ===========================================================================
# Agent 2 - Architecture
# ===========================================================================

MOCKS["architecture"] = {
    "board": "Arduino Uno R3 (ATmega328P)",
    "summary": (
        "Arduino Uno R3 controls a two-wheel differential-drive robot through "
        "an L298N motor driver. An HC-SR04 ultrasonic sensor measures obstacle "
        "distance and an MG995 servo positions the sensor. A computer running "
        "the Python agent and navigation pipeline communicates over USB serial. "
        "The design uses non-blocking control timing and a fail-safe motor stop."
    ),
    "components": [
        {
            "ref": "U1",
            "part": "Arduino Uno R3",
            "role": "Primary microcontroller"
        },
        {
            "ref": "U2",
            "part": "L298N dual H-bridge motor driver",
            "role": "Two DC motor direction and speed control"
        },
        {
            "ref": "U3",
            "part": "HC-SR04 ultrasonic distance sensor",
            "role": "Obstacle distance measurement"
        },
        {
            "ref": "S1",
            "part": "MG995 servo motor",
            "role": "Ultrasonic sensor positioning"
        },
        {
            "ref": "M1",
            "part": "DC gear motor (left)",
            "role": "Left wheel actuator"
        },
        {
            "ref": "M2",
            "part": "DC gear motor (right)",
            "role": "Right wheel actuator"
        },
        {
            "ref": "C1",
            "part": "Computer running Python navigation software",
            "role": "Multi-agent pipeline, path planning and serial communication"
        },
    ],
    "pin_map": [
        {
            "signal": "MOTOR_A_ENA",
            "gpio": 5,
            "direction": "pwm",
            "connected_to": "U2 ENA",
            "note": "Left motor speed control"
        },
        {
            "signal": "MOTOR_A_IN1",
            "gpio": 7,
            "direction": "output",
            "connected_to": "U2 IN1",
            "note": "Left motor direction"
        },
        {
            "signal": "MOTOR_A_IN2",
            "gpio": 8,
            "direction": "output",
            "connected_to": "U2 IN2",
            "note": "Left motor direction"
        },
        {
            "signal": "MOTOR_B_ENB",
            "gpio": 6,
            "direction": "pwm",
            "connected_to": "U2 ENB",
            "note": "Right motor speed control"
        },
        {
            "signal": "MOTOR_B_IN3",
            "gpio": 9,
            "direction": "output",
            "connected_to": "U2 IN3",
            "note": "Right motor direction"
        },
        {
            "signal": "MOTOR_B_IN4",
            "gpio": 10,
            "direction": "output",
            "connected_to": "U2 IN4",
            "note": "Right motor direction"
        },
        {
            "signal": "SONAR_TRIG",
            "gpio": 11,
            "direction": "output",
            "connected_to": "U3 TRIG",
            "note": "Ultrasonic trigger"
        },
        {
            "signal": "SONAR_ECHO",
            "gpio": 12,
            "direction": "input",
            "connected_to": "U3 ECHO",
            "note": "Ultrasonic echo input"
        },
        {
            "signal": "SERVO_SCAN",
            "gpio": 13,
            "direction": "output",
            "connected_to": "S1 SIG",
            "note": "MG995 servo control using Servo library"
        },
    ],
    "power": {
        "controller_supply": "Arduino Uno compatible regulated supply",
        "motor_supply": (
            "External motor supply matched to the actual DC motor voltage "
            "and current ratings, connected through the L298N."
        ),
        "servo_supply": (
            "Separate regulated 5-6 V supply with adequate current capacity "
            "for the MG995."
        ),
        "common_ground_required": True,
        "battery_configuration": "Not yet confirmed",
        "notes": (
            "Do not power the MG995 directly from an Arduino GPIO or rely on "
            "the Uno 5 V pin to supply its motor current."
        ),
    },
    "state_machine": {
        "initial": "STOPPED",
        "states": [
            {
                "name": "STOPPED",
                "entry": "Both motor enable signals are set to zero."
            },
            {
                "name": "FORWARD",
                "entry": "Both motors move forward at the configured speed."
            },
            {
                "name": "TURNING",
                "entry": "Differential motor control performs a timed turn."
            },
            {
                "name": "OBSTACLE",
                "entry": "Both motors stop while obstacle data is processed."
            },
        ],
        "transitions": [
            {
                "from": "STOPPED",
                "to": "FORWARD",
                "when": "A valid forward command is received and the path is clear."
            },
            {
                "from": "FORWARD",
                "to": "OBSTACLE",
                "when": "A valid obstacle measurement is below the safety threshold."
            },
            {
                "from": "OBSTACLE",
                "to": "TURNING",
                "when": "The navigation controller issues a valid turn command."
            },
            {
                "from": "TURNING",
                "to": "STOPPED",
                "when": "The configured turn duration ends."
            },
            {
                "from": "FORWARD",
                "to": "STOPPED",
                "when": "A stop command, sensor fault or communication timeout occurs."
            },
        ],
    },
    "timing": {
        "loop_hz": 50,
        "loop_period_ms": 20,
        "sonar_period_ms": 60,
        "telemetry_baud": 115200,
        "command_timeout_ms": 1000,
    },
    "constants": {
        "STOP_DISTANCE_CM": 20,
        "CLEAR_DISTANCE_CM": 30,
        "CRUISE_SPEED": 150,
        "TURN_SPEED": 150,
        "SERVO_CENTER_DEG": 90,
        "SERVO_LEFT_DEG": 150,
        "SERVO_RIGHT_DEG": 30,
        "SERVO_SETTLE_MS": 300,
    },
    "modules": [
        {
            "name": "motors",
            "responsibility": "L298N direction and PWM speed control."
        },
        {
            "name": "ultrasonic",
            "responsibility": "HC-SR04 trigger, echo timing and distance calculation."
        },
        {
            "name": "servo",
            "responsibility": "MG995 positioning for directional sensor scans."
        },
        {
            "name": "control",
            "responsibility": "Safe motor control and robot state transitions."
        },
        {
            "name": "communication",
            "responsibility": "USB serial commands and telemetry."
        },
    ],
    "safety": (
        "motorsStop() is called during setup before any motor movement. "
        "Both motors stop when an obstacle is detected within the configured "
        "threshold. Invalid ultrasonic readings and echo timeouts are treated "
        "as unsafe measurements. Invalid commands and serial communication "
        "timeouts must result in a motor stop. The MG995 uses a separate "
        "regulated supply and all relevant grounds are common."
    ),
}


# ===========================================================================
# Agent 3 - Firmware
# ===========================================================================

MOCKS["firmware"] = {
    "files": [
        {
            "path": "robot_controller/robot_controller.ino",
            "language": "cpp",
            "description": "Arduino Uno R3 autonomous obstacle-avoidance controller",
            "content": r"""/*
 * robot_controller.ino
 * Arduino Uno R3 - autonomous obstacle-avoidance robot.
 *
 * Controller: Arduino Uno R3 / ATmega328P
 * Motor driver: L298N
 * Distance sensor: HC-SR04
 * Sensor positioning: MG995 servo
 *
 * Generated by the multi-agent firmware pipeline.
 */

#include <Arduino.h>
#include <Servo.h>

// --------------------------------------------------------------- pin map

#define MOTOR_A_ENA 5
#define MOTOR_A_IN1 7
#define MOTOR_A_IN2 8

#define MOTOR_B_ENB 6
#define MOTOR_B_IN3 9
#define MOTOR_B_IN4 10

#define SONAR_TRIG 11
#define SONAR_ECHO 12

#define SERVO_SCAN 13

// -------------------------------------------------------------- constants

static const unsigned long LOOP_INTERVAL_MS = 20;
static const unsigned long SONAR_INTERVAL_MS = 60;
static const unsigned long ECHO_TIMEOUT_US = 25000UL;
static const unsigned long COMMAND_TIMEOUT_MS = 1000;

static const int STOP_DISTANCE_CM = 20;
static const int CRUISE_SPEED = 150;
static const int TURN_SPEED = 150;

static const int SERVO_CENTER_DEG = 90;
static const int SERVO_LEFT_DEG = 150;
static const int SERVO_RIGHT_DEG = 30;

// ----------------------------------------------------------------- objects

Servo scanServo;

// ------------------------------------------------------------------ state

enum RobotState {
    STOPPED,
    FORWARD,
    TURNING,
    OBSTACLE
};

static RobotState robotState = STOPPED;

static unsigned long lastLoopMs = 0;
static unsigned long lastSonarMs = 0;
static unsigned long lastCommandMs = 0;
static unsigned long stateSinceMs = 0;

static int distanceCm = -1;
static bool sensorFault = true;

// --------------------------------------------------------------- motors

static void motorsStop() {
    analogWrite(MOTOR_A_ENA, 0);
    analogWrite(MOTOR_B_ENB, 0);

    digitalWrite(MOTOR_A_IN1, LOW);
    digitalWrite(MOTOR_A_IN2, LOW);
    digitalWrite(MOTOR_B_IN3, LOW);
    digitalWrite(MOTOR_B_IN4, LOW);
}

static void motorsForward(int speedValue) {
    digitalWrite(MOTOR_A_IN1, HIGH);
    digitalWrite(MOTOR_A_IN2, LOW);

    digitalWrite(MOTOR_B_IN3, HIGH);
    digitalWrite(MOTOR_B_IN4, LOW);

    analogWrite(MOTOR_A_ENA, constrain(speedValue, 0, 255));
    analogWrite(MOTOR_B_ENB, constrain(speedValue, 0, 255));
}

static void motorsTurnRight(int speedValue) {
    digitalWrite(MOTOR_A_IN1, LOW);
    digitalWrite(MOTOR_A_IN2, HIGH);

    digitalWrite(MOTOR_B_IN3, HIGH);
    digitalWrite(MOTOR_B_IN4, LOW);

    analogWrite(MOTOR_A_ENA, constrain(speedValue, 0, 255));
    analogWrite(MOTOR_B_ENB, constrain(speedValue, 0, 255));
}

// -------------------------------------------------------------- ultrasonic

enum SonarPhase {
    SONAR_IDLE,
    SONAR_WAIT_RISE,
    SONAR_WAIT_FALL
};

static SonarPhase sonarPhase = SONAR_IDLE;
static unsigned long echoStartUs = 0;

static void startSonarMeasurement() {
    digitalWrite(SONAR_TRIG, LOW);
    delayMicroseconds(2);

    digitalWrite(SONAR_TRIG, HIGH);
    delayMicroseconds(10);

    digitalWrite(SONAR_TRIG, LOW);

    echoStartUs = micros();
    sonarPhase = SONAR_WAIT_RISE;
}

static void updateSonar() {
    unsigned long nowUs = micros();

    if (sonarPhase == SONAR_WAIT_RISE) {
        if (digitalRead(SONAR_ECHO) == HIGH) {
            echoStartUs = nowUs;
            sonarPhase = SONAR_WAIT_FALL;
        } else if (nowUs - echoStartUs > ECHO_TIMEOUT_US) {
            distanceCm = 0;
            sensorFault = true;
            sonarPhase = SONAR_IDLE;
        }
    }
    else if (sonarPhase == SONAR_WAIT_FALL) {
        if (digitalRead(SONAR_ECHO) == LOW) {
            unsigned long pulseWidth = nowUs - echoStartUs;
            distanceCm = (int)(pulseWidth / 58UL);
            sensorFault = (distanceCm <= 0);
            sonarPhase = SONAR_IDLE;
        } else if (nowUs - echoStartUs > ECHO_TIMEOUT_US) {
            distanceCm = 0;
            sensorFault = true;
            sonarPhase = SONAR_IDLE;
        }
    }
}

// -------------------------------------------------------------- serial I/O

static void processSerialCommands() {
    while (Serial.available() > 0) {
        char command = (char)Serial.read();
        lastCommandMs = millis();

        if (command == 'F') {
            if (!sensorFault && distanceCm >= STOP_DISTANCE_CM) {
                robotState = FORWARD;
                motorsForward(CRUISE_SPEED);
            } else {
                robotState = OBSTACLE;
                motorsStop();
            }
        }
        else if (command == 'R') {
            robotState = TURNING;
            motorsTurnRight(TURN_SPEED);
            stateSinceMs = millis();
        }
        else if (command == 'S') {
            robotState = STOPPED;
            motorsStop();
        }
        else if (command == 'C') {
            scanServo.write(SERVO_CENTER_DEG);
        }
        else if (command == 'L') {
            scanServo.write(SERVO_LEFT_DEG);
        }
        else if (command == 'Q') {
            scanServo.write(SERVO_RIGHT_DEG);
        }
        else {
            robotState = STOPPED;
            motorsStop();
        }
    }
}

static void sendTelemetry() {
    Serial.print("{\"state\":");

    switch (robotState) {
        case STOPPED:
            Serial.print("\"STOPPED\"");
            break;
        case FORWARD:
            Serial.print("\"FORWARD\"");
            break;
        case TURNING:
            Serial.print("\"TURNING\"");
            break;
        case OBSTACLE:
            Serial.print("\"OBSTACLE\"");
            break;
    }

    Serial.print(",\"distance_cm\":");
    Serial.print(distanceCm);

    Serial.print(",\"sensor_fault\":");
    Serial.print(sensorFault ? "true" : "false");

    Serial.println("}");
}

// ------------------------------------------------------------------- setup

void setup() {
    Serial.begin(115200);

    pinMode(MOTOR_A_ENA, OUTPUT);
    pinMode(MOTOR_A_IN1, OUTPUT);
    pinMode(MOTOR_A_IN2, OUTPUT);

    pinMode(MOTOR_B_ENB, OUTPUT);
    pinMode(MOTOR_B_IN3, OUTPUT);
    pinMode(MOTOR_B_IN4, OUTPUT);

    pinMode(SONAR_TRIG, OUTPUT);
    pinMode(SONAR_ECHO, INPUT);

    motorsStop();

    scanServo.attach(SERVO_SCAN);
    scanServo.write(SERVO_CENTER_DEG);

    lastCommandMs = millis();
    lastSonarMs = millis();
    lastLoopMs = millis();

    robotState = STOPPED;
}

// -------------------------------------------------------------------- loop

void loop() {
    unsigned long now = millis();

    if (now - lastLoopMs < LOOP_INTERVAL_MS) {
        return;
    }

    lastLoopMs = now;

    updateSonar();

    if (sonarPhase == SONAR_IDLE &&
        now - lastSonarMs >= SONAR_INTERVAL_MS) {
        lastSonarMs = now;
        startSonarMeasurement();
    }

    processSerialCommands();

    // Fail-safe: invalid sensor readings stop the robot.
    if (sensorFault &&
        (robotState == FORWARD || robotState == TURNING)) {
        robotState = OBSTACLE;
        motorsStop();
    }

    // Stop when an obstacle is too close.
    if (distanceCm >= 0 &&
        distanceCm < STOP_DISTANCE_CM &&
        robotState == FORWARD) {
        robotState = OBSTACLE;
        motorsStop();
    }

    // Stop if computer commands are no longer received.
    if (robotState != STOPPED &&
        now - lastCommandMs > COMMAND_TIMEOUT_MS) {
        robotState = STOPPED;
        motorsStop();
    }

    sendTelemetry();
}
""",
        }
    ],
    "library_dependencies": [
        {
            "name": "Servo",
            "version": "Arduino AVR Servo library",
            "source": "Arduino IDE library manager / AVR core"
        }
    ],
    "build_notes": [
        "Target board: Arduino Uno R3.",
        "Target processor: ATmega328P.",
        "Use the Arduino AVR Boards package.",
        "Select Arduino Uno in Arduino IDE.",
        "Serial communication uses 115200 baud.",
        "Use the Servo library for MG995 control.",
        "Use external motor and servo supplies with a common ground.",
        "Verify the actual motor and servo supply ratings before connecting power."
    ],
    "self_check": [
        "All hardware pin definitions match the validated Arduino Uno architecture.",
        "Motor speed uses analogWrite() on PWM-capable pins 5 and 6.",
        "Motor direction uses digitalWrite() on the assigned direction pins.",
        "MG995 uses the Servo library on digital pin 13.",
        "The control loop uses millis()-based scheduling.",
        "The ultrasonic echo measurement uses micros() and a timeout.",
        "motorsStop() is called during setup before motor movement.",
        "Invalid ultrasonic measurements trigger a fail-safe stop.",
        "Serial communication is initialized at 115200 baud.",
        "The firmware does not use ESP32-specific APIs."
    ],
}
