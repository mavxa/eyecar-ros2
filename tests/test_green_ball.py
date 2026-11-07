"""Check the procedural mesh, including the four regions between the bands."""
from collections import defaultdict
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node.js is needed to evaluate the Webots template')
class GreenBallTests(unittest.TestCase):
    def test_closed_sphere_with_four_green_regions(self):
        proto = (ROOT/'ros2_ws/src/eyecar_sim/protos/GreenBall.proto').read_text()
        script = proto.split('%<', 1)[1].split('>%', 1)[0]
        data = json.loads(subprocess.check_output([
            'node', '-e', 'const fields={radius:{value:0.04},bandWidth:{value:0.008}};'
            +script+'; console.log(JSON.stringify({points,faces,colors}));'], text=True))
        points, faces, colors = (data[key] for key in ('points', 'faces', 'colors'))
        edges = defaultdict(list)
        for index, face in enumerate(faces):
            self.assertEqual(len(set(face)), len(face))
            for a, b in zip(face, face[1:]+face[:1]):
                edges[tuple(sorted((a, b)))].append(index)
        self.assertTrue(all(len(owners) == 2 for owners in edges.values()))
        self.assertEqual(len(points)-len(edges)+len(faces), 2)
        for point in points:
            self.assertAlmostEqual(sum(v*v for v in point), 0.04**2)
        neighbours = defaultdict(set)
        for a, b in edges.values():
            if colors[a] == colors[b] == 0:
                neighbours[a].add(b)
                neighbours[b].add(a)
        unseen = {i for i, color in enumerate(colors) if color == 0}
        regions = 0
        while unseen:
            pending = [unseen.pop()]
            regions += 1
            while pending:
                for neighbour in neighbours[pending.pop()] & unseen:
                    unseen.remove(neighbour)
                    pending.append(neighbour)
        self.assertEqual(regions, 4)
        self.assertIn(1, colors)


if __name__ == '__main__':
    unittest.main()
