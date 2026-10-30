import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from eyecar_wiring import PI_ROWS, mega_diagram, overview, pinmap, pi_diagram


class WiringDocsTests(unittest.TestCase):
    def setUp(self):
        self.firmware = (ROOT / 'firmware/eyecar_base_controller/eyecar_base_controller.ino').read_text()
        self.led = (ROOT / 'ros2_ws/src/eyecar_led/eyecar_led/led_strip.py').read_text()

    def test_pin_change_reaches_diagram_and_conflicts_are_rejected(self):
        changed = self.firmware.replace('MOTOR_PIN = 3;', 'MOTOR_PIN = 9;')
        self.assertIn('D9 / S9', mega_diagram(pinmap(changed, self.led)))
        conflicting = self.firmware.replace('MOTOR_PIN = 3;', 'MOTOR_PIN = 2;')
        with self.assertRaises(ValueError):
            pinmap(conflicting, self.led)

    def test_gpio_numbering_and_svg_output(self):
        pins = pinmap(self.firmware, self.led)
        self.assertEqual(len(PI_ROWS), 20)
        self.assertEqual(PI_ROWS[5][1], 'GPIO18')
        self.assertEqual(pins['led_physical'], 12)
        self.assertEqual(pins['led_count'], 13)
        for make in (mega_diagram, pi_diagram, overview):
            ET.fromstring(make(pins))


if __name__ == '__main__':
    unittest.main()
