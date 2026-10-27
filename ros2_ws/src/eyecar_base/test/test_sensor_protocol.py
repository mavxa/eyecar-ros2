import unittest

from eyecar_base.sensor_protocol import parse_sensor_line


class SensorProtocolTests(unittest.TestCase):
    def test_ultrasonic_zero_means_no_echo(self):
        self.assertEqual(parse_sensor_line('US 0 0 84 21'), ('US', [0, 0, 84, 21]))

    def test_analog_and_digital_ir(self):
        self.assertEqual(parse_sensor_line('IR 947 0 1 0 250'),
                         ('IR', [947, 0, 1, 0, 250]))
        self.assertEqual(parse_sensor_line('IR 1 0 1 0 1'), ('IR', [1, 0, 1, 0, 1]))

    def test_control_protocol_is_not_telemetry(self):
        for line in ('', 'ACK 1 1500 1500', 'READY EYECAR_BASE_V1', 'WATCHDOG STOP'):
            self.assertIsNone(parse_sensor_line(line))

    def test_bad_count_range_or_format_is_rejected(self):
        for line in ('US 1 2 3', 'US 1 2 3 4 5', 'US 401 1 1 1',
                     'US -1 0 0 0', 'IR 1024 0 0 0 0', 'IR 1.2 0 0 0 0',
                     'IR x 0 0 0 0'):
            with self.assertRaises(ValueError):
                parse_sensor_line(line)


if __name__ == '__main__':
    unittest.main()
