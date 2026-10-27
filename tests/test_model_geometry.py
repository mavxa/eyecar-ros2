import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from eyecar_model import make_urdf, parts_for


class ModelGeometryTests(unittest.TestCase):
    def setUp(self):
        self.dimensions = json.loads((ROOT/'models/eyecar/dimensions.json').read_text())
        self.parts = {part['name']: part for part in parts_for(self.dimensions)}
        self.robot = ET.fromstring(make_urdf(self.dimensions,list(self.parts.values())))

    def test_sonars_and_sensor_frames_share_electronics_height(self):
        heights = {sensor['z'] for sensor in self.dimensions['sensors']}
        self.assertEqual(len(heights),1)
        height = heights.pop()
        plate = self.parts['electronics_plate']['center'][2]
        self.assertGreater(height,plate)
        self.assertLess(height,plate+0.025)
        for sensor in self.dimensions['sensors']:
            name = sensor['name']
            self.assertEqual(self.parts[f'us_{name}_pcb']['center'][2],height)
            origin = self.robot.find(f"joint[@name='us_{name}_mount']/origin")
            self.assertAlmostEqual(float(origin.attrib['xyz'].split()[2]),height)

    def test_camera_fits_inside_holder_and_tf_matches_visual(self):
        camera = self.parts['camera_bar']
        holder = next(part for name,part in self.parts.items() if name.startswith('camera_holder_') and name!='camera_holder_bar')
        center = camera['center'][2]
        self.assertAlmostEqual(center,holder['center'][2])
        self.assertLessEqual(camera['size'][2],holder['size'][2])
        origin = self.robot.find("joint[@name='camera_mount']/origin")
        self.assertAlmostEqual(float(origin.attrib['xyz'].split()[2]),center)
        self.assertEqual(self.parts['camera_lens']['center'][2],center)


if __name__ == '__main__':
    unittest.main()
