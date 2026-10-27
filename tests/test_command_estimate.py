import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from eyecar_motion import CommandEstimate


class CommandEstimateTests(unittest.TestCase):
    def setUp(self):
        self.dimensions = json.loads((ROOT/'models/eyecar/dimensions.json').read_text())
        self.motion = CommandEstimate(self.dimensions)

    def drive(self, speed, steer, duration=1.0):
        for i in range(round(duration/0.05)+1):
            now = i*0.05
            self.motion.set_command(speed, steer, now)
            self.motion.step(now)

    def test_one_second_straight_motion(self):
        self.drive(0.18,0.0)
        self.assertAlmostEqual(self.motion.x,0.18,places=6)
        self.assertAlmostEqual(self.motion.y,0.0)
        self.assertAlmostEqual(self.motion.yaw,0.0)

    def test_steering_without_speed_does_not_turn_car_in_place(self):
        self.drive(0.0,0.85)
        self.assertEqual((self.motion.x,self.motion.y,self.motion.yaw),(0.0,0.0,0.0))
        self.assertGreater(self.motion.steering,0)

    def test_reverse_reverses_turn_direction(self):
        self.drive(-0.18,0.5)
        self.assertLess(self.motion.x,0)
        self.assertLess(self.motion.yaw,0)

    def test_stale_commands_stop_prediction_and_wheels(self):
        self.drive(0.18,0.5)
        self.motion.step(1.6)
        pose = (self.motion.x,self.motion.y,self.motion.yaw,self.motion.wheel_angle)
        self.motion.step(1.7)
        self.assertEqual(pose,(self.motion.x,self.motion.y,self.motion.yaw,self.motion.wheel_angle))
        self.assertEqual(self.motion.speed,0)

    def test_inner_wheel_turns_more_and_reset_clears_input(self):
        self.drive(0.1,0.85)
        left,right = self.motion.steering_angles()
        self.assertGreater(left,right)
        self.assertTrue(0<right<left<math.pi/2)
        self.motion.reset()
        self.assertFalse(self.motion.step(5.0))
        self.assertEqual(self.motion.x,0.0)


if __name__ == '__main__':
    unittest.main()
