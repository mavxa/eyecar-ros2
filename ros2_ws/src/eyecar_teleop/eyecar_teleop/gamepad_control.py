"""Validated gamepad commands, dead zone and release-to-rearm watchdog."""

from __future__ import annotations

import json
import math


class GamepadControl:
    def __init__(self, timeout=0.4, deadzone=0.12):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('timeout must be positive and finite')
        if not math.isfinite(deadzone) or not 0 <= deadzone < 1:
            raise ValueError('deadzone must be in [0, 1)')
        self.timeout = timeout
        self.deadzone = deadzone
        self.last_input = None
        self.ready = False
        self.throttle = 0.0
        self.steering = 0.0

    def stop(self):
        self.ready = False
        self.throttle = self.steering = 0.0

    def axis(self, value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('axis must be a finite number')
        if not -1 <= value <= 1:
            raise ValueError('axis must be in [-1, 1]')
        if abs(value) <= self.deadzone:
            return 0.0
        return math.copysign(
            (abs(value) - self.deadzone) / (1 - self.deadzone), value)

    def receive(self, line, now):
        # A timeout must disarm even when a new packet arrives before a timer tick.
        self.command(now)
        try:
            packet = json.loads(line)
            if not isinstance(packet, dict):
                raise ValueError('expected an object')
            throttle = self.axis(packet['throttle'])
            steering = self.axis(packet['steering'])
            enabled = packet['enabled']
            emergency = packet.get('stop', False)
            if type(enabled) is not bool or type(emergency) is not bool:
                raise ValueError('enabled and stop must be booleans')
        except (ValueError, KeyError, TypeError):
            self.stop()
            return False
        self.last_input = now
        if emergency:
            self.stop()
        elif not enabled:
            self.throttle = self.steering = 0.0
            self.ready = throttle == 0.0 and steering == 0.0
        elif self.ready:
            self.throttle, self.steering = throttle, steering
        return True

    def command(self, now):
        if self.last_input is None or now - self.last_input >= self.timeout:
            self.stop()
        return self.throttle, self.steering
