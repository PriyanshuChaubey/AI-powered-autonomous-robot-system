
#define TRIG_PIN 11
#define ECHO_PIN 12

#define SAMPLES 7
#define MAX_DISTANCE_CM 400

float readings[SAMPLES];

float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(
    ECHO_PIN,
    HIGH,
    25000UL
  );

  if (duration == 0) {
    return -1;
  }

  float distance = duration * 0.0343f / 2.0f;

  if (distance < 2 || distance > MAX_DISTANCE_CM) {
    return -1;
  }

  return distance;
}

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(TRIG_PIN, LOW);

  Serial.println("HC-SR04 Diagnostic Test");
}

void loop() {
  int validCount = 0;

  for (int i = 0; i < SAMPLES; i++) {
    float distance = getDistance();

    if (distance > 0) {
      readings[validCount++] = distance;
    }

    delay(60);
  }

  if (validCount < 4) {
    Serial.println("ERROR: Insufficient valid readings");
    return;
  }

  // Sort valid readings.
  for (int i = 0; i < validCount - 1; i++) {
    for (int j = i + 1; j < validCount; j++) {
      if (readings[i] > readings[j]) {
        float temp = readings[i];
        readings[i] = readings[j];
        readings[j] = temp;
      }
    }
  }

  // Median reading.
  float median = readings[validCount / 2];

  Serial.print("Valid samples: ");
  Serial.print(validCount);

  Serial.print(" | Median distance: ");
  Serial.print(median, 1);

  Serial.println(" cm");

  delay(300);
}
