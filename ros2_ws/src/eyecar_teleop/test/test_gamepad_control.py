import json
import unittest

from eyecar_teleop.gamepad_control import GamepadControl


class GamepadSafetyTests(unittest.TestCase):
    def setUp(self):
        self.control = GamepadControl()

    def packet(self, now, throttle=0.0, steering=0.0, enabled=False, stop=False):
        return self.control.receive(json.dumps(dict(
            throttle=throttle, steering=steering, enabled=enabled, stop=stop)), now)

    def arm(self):
        self.packet(1.0)
        self.packet(1.1, throttle=1.0, steering=-1.0, enabled=True)

    def test_held_enable_on_start_cannot_move(self):
        self.packet(1.0, throttle=1.0, enabled=True)
        self.assertEqual(self.control.command(1.1), (0.0, 0.0))

    def test_release_requires_centered_sticks(self):
        self.packet(1.0, throttle=0.5)
        self.packet(1.1, throttle=1.0, enabled=True)
        self.assertEqual(self.control.command(1.2), (0.0, 0.0))
        self.arm()
        self.assertEqual(self.control.command(1.2), (1.0, -1.0))
        self.packet(1.3, enabled=False)
        self.assertEqual(self.control.command(1.3), (0.0, 0.0))

    def test_timeout_requires_release_before_resuming(self):
        self.arm()
        self.assertEqual(self.control.command(1.6), (0.0, 0.0))
        self.packet(1.7, throttle=1.0, enabled=True)
        self.assertEqual(self.control.command(1.7), (0.0, 0.0))
        self.packet(1.8)
        self.packet(1.9, throttle=1.0, enabled=True)
        self.assertEqual(self.control.command(1.9), (1.0, 0.0))

    def test_packet_after_timeout_disarms_without_timer_tick(self):
        self.arm()
        self.packet(2.0, throttle=1.0, enabled=True)
        self.assertEqual(self.control.command(2.0), (0.0, 0.0))

    def test_emergency_stop_requires_release(self):
        self.arm()
        self.packet(1.2, throttle=1.0, enabled=True, stop=True)
        self.packet(1.3, throttle=1.0, enabled=True)
        self.assertEqual(self.control.command(1.3), (0.0, 0.0))

    def test_malformed_or_nonfinite_input_stops(self):
        for line in ('bad', '[]', '{}', '{"throttle":NaN}',
                     '{"throttle":1,"steering":0,"enabled":1}',
                     '{"throttle":2,"steering":0,"enabled":true}',
                     '{"throttle":true,"steering":0,"enabled":true}'):
            self.arm()
            self.assertFalse(self.control.receive(line, 1.2))
            self.assertEqual(self.control.command(1.2), (0.0, 0.0))

    def test_deadzone_and_reverse(self):
        self.packet(1.0, throttle=0.1, steering=-0.1)
        self.packet(1.1, throttle=-1.0, steering=0.1, enabled=True)
        self.assertEqual(self.control.command(1.2), (-1.0, 0.0))


if __name__ == '__main__':
    unittest.main()
