"""Check image selection without opening a window or contacting the rover."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RvizLauncherTests(unittest.TestCase):
    def test_build_and_launch_share_the_development_image(self):
        with tempfile.TemporaryDirectory() as folder:
            docker = Path(folder) / 'docker'
            docker.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = image ] && [ "$2" = inspect ]; then\n'
                '  [ "$3" = eyecar-ros2:jazzy ]\n'
                'else\n  printf "%s\\n" "$@"\nfi\n')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=folder + ':' + os.environ['PATH'])
            env.pop('DISPLAY', None)
            command = ['bash', str(ROOT / 'scripts/eyecar-rviz')]
            build = subprocess.run(command + ['build'], env=env, text=True,
                                   capture_output=True, check=True)
            image = 'eyecar-ros2:jazzy'
            self.assertIn(image, build.stdout.splitlines())
            self.assertIn('image: ' + image, (ROOT / 'compose.yaml').read_text())
            launch = subprocess.run(command, env=env, text=True, capture_output=True)
            self.assertNotEqual(launch.returncode, 0)
            self.assertIn('graphical laptop session', launch.stderr)
            self.assertNotIn('Build first', launch.stderr)


if __name__ == '__main__':
    unittest.main()
