#include <Servo.h>

// KvantoShield PLS signal row: motor on S3, steering servo on S2.
// Pulse limits are based on the bundled EyeCar examples and live calibration.
constexpr uint8_t MOTOR_PIN = 3;
constexpr uint8_t STEERING_PIN = 2;
constexpr int MOTOR_NEUTRAL_US = 1500;
constexpr int MOTOR_FORWARD_RANGE_US = 130;
constexpr int MOTOR_REVERSE_RANGE_US = 150;
constexpr int STEERING_CENTER_US = 1500;
constexpr int STEERING_RANGE_US = 200;
constexpr int THROTTLE_DIRECTION = 1;
constexpr int STEERING_DIRECTION = 1;
constexpr unsigned long COMMAND_TIMEOUT_MS = 400;
constexpr unsigned long ESC_ARM_TIME_MS = 1500;
constexpr unsigned long REVERSE_BRAKE_TIME_MS = 180;
constexpr unsigned long REVERSE_NEUTRAL_TIME_MS = 180;
constexpr unsigned long SERIAL_BAUD = 115200;

Servo motor;
Servo steering;

char line_buffer[48];
uint8_t line_length = 0;
unsigned long last_command_ms = 0;
bool watchdog_reported = false;
int requested_throttle = 0;
int requested_steer = 0;
int actual_motor_us = MOTOR_NEUTRAL_US;
int actual_steering_us = STEERING_CENTER_US;

enum ReverseStage : uint8_t {
  REVERSE_IDLE,
  REVERSE_BRAKE,
  REVERSE_NEUTRAL,
  REVERSE_ACTIVE,
};

ReverseStage reverse_stage = REVERSE_IDLE;
unsigned long reverse_stage_started_ms = 0;

int clampCommand(int value) {
  if (value < -1000) {
    return -1000;
  }
  if (value > 1000) {
    return 1000;
  }
  return value;
}

void stopBase() {
  requested_throttle = 0;
  requested_steer = 0;
  reverse_stage = REVERSE_IDLE;
  actual_motor_us = MOTOR_NEUTRAL_US;
  actual_steering_us = STEERING_CENTER_US;
  motor.writeMicroseconds(MOTOR_NEUTRAL_US);
  steering.writeMicroseconds(STEERING_CENTER_US);
}

int motorPulseForCommand(int throttle) {
  const int motor_range_us = throttle >= 0
      ? MOTOR_FORWARD_RANGE_US
      : MOTOR_REVERSE_RANGE_US;
  return MOTOR_NEUTRAL_US
      + static_cast<int32_t>(THROTTLE_DIRECTION) * throttle
          * motor_range_us / 1000;
}

int steeringPulseForCommand(int steer) {
  return STEERING_CENTER_US
      + static_cast<int32_t>(STEERING_DIRECTION) * steer
          * STEERING_RANGE_US / 1000;
}

void writeOutputs(int motor_us, int steering_us) {
  actual_motor_us = motor_us;
  actual_steering_us = steering_us;
  motor.writeMicroseconds(actual_motor_us);
  steering.writeMicroseconds(actual_steering_us);
}

void applyCommand(int throttle, int steer) {
  throttle = clampCommand(throttle);
  steer = clampCommand(steer);
  const bool entering_reverse = throttle < 0 && requested_throttle >= 0;
  requested_throttle = throttle;
  requested_steer = steer;

  if (throttle >= 0) {
    reverse_stage = REVERSE_IDLE;
    writeOutputs(
        motorPulseForCommand(throttle),
        steeringPulseForCommand(steer));
    return;
  }

  if (entering_reverse) {
    reverse_stage = REVERSE_BRAKE;
    reverse_stage_started_ms = millis();
    writeOutputs(
        MOTOR_NEUTRAL_US - MOTOR_REVERSE_RANGE_US,
        steeringPulseForCommand(steer));
    return;
  }

  if (reverse_stage == REVERSE_ACTIVE) {
    writeOutputs(
        motorPulseForCommand(throttle),
        steeringPulseForCommand(steer));
  } else {
    writeOutputs(actual_motor_us, steeringPulseForCommand(steer));
  }
}

void updateReverseSequence() {
  if (requested_throttle >= 0) {
    return;
  }

  const unsigned long stage_age = millis() - reverse_stage_started_ms;
  if (reverse_stage == REVERSE_BRAKE
      && stage_age >= REVERSE_BRAKE_TIME_MS) {
    reverse_stage = REVERSE_NEUTRAL;
    reverse_stage_started_ms = millis();
    writeOutputs(MOTOR_NEUTRAL_US, steeringPulseForCommand(requested_steer));
  } else if (reverse_stage == REVERSE_NEUTRAL
      && stage_age >= REVERSE_NEUTRAL_TIME_MS) {
    reverse_stage = REVERSE_ACTIVE;
    writeOutputs(
        motorPulseForCommand(requested_throttle),
        steeringPulseForCommand(requested_steer));
  }
}

void handleLine(char *line) {
  if (strcmp(line, "STOP") == 0) {
    stopBase();
    last_command_ms = millis();
    watchdog_reported = false;
    Serial.println(F("ACK STOP"));
    return;
  }

  unsigned long sequence = 0;
  int throttle = 0;
  int steer = 0;
  if (sscanf(line, "C %lu %d %d", &sequence, &throttle, &steer) == 3) {
    applyCommand(throttle, steer);
    last_command_ms = millis();
    watchdog_reported = false;
    Serial.print(F("ACK "));
    Serial.print(sequence);
    Serial.print(' ');
    Serial.print(actual_motor_us);
    Serial.print(' ');
    Serial.println(actual_steering_us);
    return;
  }

  stopBase();
  Serial.println(F("ERR BAD_COMMAND"));
}

void readSerial() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\r') {
      continue;
    }
    if (value == '\n') {
      line_buffer[line_length] = '\0';
      if (line_length > 0) {
        handleLine(line_buffer);
      }
      line_length = 0;
      continue;
    }
    if (static_cast<size_t>(line_length) + 1 < sizeof(line_buffer)) {
      line_buffer[line_length++] = value;
    } else {
      line_length = 0;
      stopBase();
      Serial.println(F("ERR LINE_TOO_LONG"));
    }
  }
}

void setup() {
  motor.attach(MOTOR_PIN);
  steering.attach(STEERING_PIN);
  stopBase();

  Serial.begin(SERIAL_BAUD);
  delay(ESC_ARM_TIME_MS);
  last_command_ms = millis();
  Serial.println(F("READY EYECAR_BASE_V1"));
}

void loop() {
  readSerial();
  updateReverseSequence();

  if (millis() - last_command_ms > COMMAND_TIMEOUT_MS) {
    stopBase();
    if (!watchdog_reported) {
      Serial.println(F("WATCHDOG STOP"));
      watchdog_reported = true;
    }
  }
}
