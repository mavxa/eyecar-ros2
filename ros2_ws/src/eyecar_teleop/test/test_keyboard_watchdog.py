import unittest
from unittest.mock import patch

from eyecar_teleop.keyboard_protocol import KeyEvent
from eyecar_teleop.keyboard_teleop import KeyboardTeleop


class FakeKeyboard:
    releases_available = False


class FakeLogger:
    def info(self, *args):
        pass


class Commands:
    # Use the actual node methods without starting ROS or publishing to motors.
    apply_event = KeyboardTeleop.apply_event
    on_timer = KeyboardTeleop.on_timer

    def __init__(self):
        self.keyboard = FakeKeyboard()
        self.held_keys = set()
        self.forward_speed, self.reverse_speed, self.angular_speed = .18, .25, .85
        self.command_timeout = .5
        self.linear = self.angular = 0.0
        self.last_command_at = self.last_linear_at = self.last_angular_at = 0.0
        self.quit_requested = False

    def publish_command(self):
        pass

    def get_logger(self):
        return FakeLogger()


class KeyboardWatchdogTests(unittest.TestCase):
    def event(self, control, key, now):
        with patch('eyecar_teleop.keyboard_teleop.time.monotonic', return_value=now):
            control.apply_event(KeyEvent(key))

    def timer(self, control, now):
        with patch('eyecar_teleop.keyboard_teleop.time.monotonic', return_value=now):
            control.on_timer()

    def test_steering_repeat_does_not_keep_throttle_alive(self):
        control = Commands()
        self.event(control, 'w', 1)
        self.event(control, 'a', 1.1)
        self.event(control, 'a', 1.6)
        self.timer(control, 1.6)
        self.assertEqual((control.linear, control.angular), (0, .85))

    def test_throttle_repeat_does_not_keep_steering_alive(self):
        control = Commands()
        self.event(control, 'd', 1)
        self.event(control, 'w', 1.1)
        self.event(control, 'w', 1.6)
        self.timer(control, 1.6)
        self.assertEqual((control.linear, control.angular), (.18, 0))

    def test_repeating_both_axes_and_stop(self):
        control = Commands()
        for now in (1, 1.2, 1.4, 1.6):
            self.event(control, 'w', now)
            self.event(control, 'd', now)
            self.timer(control, now)
            self.assertEqual((control.linear, control.angular), (.18, -.85))
        self.event(control, ' ', 1.7)
        self.timer(control, 1.8)
        self.assertEqual((control.linear, control.angular), (0, 0))

    def test_complete_input_loss_stops_both_axes(self):
        control = Commands()
        self.event(control, 'w', 1)
        self.event(control, 'a', 1)
        self.timer(control, 1.6)
        self.assertEqual((control.linear, control.angular), (0, 0))


if __name__ == '__main__':
    unittest.main()
