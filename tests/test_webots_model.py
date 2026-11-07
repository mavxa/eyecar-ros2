import json
import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'ros2_ws/src/eyecar_sim')]
from eyecar_webots import axis_angle, outputs
from eyecar_sim.control import ultrasonic_cm, wheel_commands


class WebotsModelTests(unittest.TestCase):
    def setUp(self):
        self.d = json.loads((ROOT/'models/eyecar/dimensions.json').read_text())

    def test_shared_geometry_and_devices(self):
        generated = outputs(self.d)
        proto = generated['protos/EyeCar.proto']
        self.assertEqual(proto.count('type "sonar"'), 4)
        self.assertEqual(proto.count('type "infra-red"'), 5)
        self.assertEqual(proto.count('gradual TRUE'), 13)
        self.assertIn('width 320 height 240', proto)
        self.assertIn(f'fieldOfView {math.pi/2}', proto)
        for wheel in ('front_left', 'front_right', 'rear_left', 'rear_right'):
            self.assertIn(f'name "{wheel}_motor"', proto)
        model = ET.fromstring(generated['config/eyecar.urdf'])
        self.assertEqual(model.find('webots/plugin').get('type'), 'eyecar_sim.driver.EyeCarDriver')
        changed = dict(self.d, plate_width=0.2)
        self.assertNotEqual(generated['protos/EyeCar.proto'], outputs(changed)['protos/EyeCar.proto'])
        self.assertEqual(axis_angle((0, 0, 0)), '0 0 1 0')

    def test_ackermann_and_invalid_commands(self):
        speeds, angles = wheel_commands(0.18, 0, self.d)
        self.assertEqual(angles, [0, 0])
        self.assertTrue(all(abs(v-7.5) < 1e-8 for v in speeds))
        self.assertEqual(wheel_commands(5, 0, self.d), wheel_commands(0.25, 0, self.d))
        speeds, angles = wheel_commands(0.18, 0.85, self.d)
        self.assertGreater(angles[0], angles[1])
        self.assertGreater(speeds[1], speeds[0])
        reverse, _ = wheel_commands(-0.18, 0.85, self.d)
        self.assertEqual(reverse, [-v for v in speeds])
        for bad in (math.nan, math.inf):
            self.assertEqual(wheel_commands(bad, 0, self.d), ([0.0]*4, [0.0]*2))
        self.assertEqual(ultrasonic_cm(0.25), 25)
        self.assertEqual(ultrasonic_cm(4), 0)
        self.assertEqual(ultrasonic_cm(math.nan), 0)


if __name__ == '__main__':
    unittest.main()
