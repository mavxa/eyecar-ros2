import json
import os
from pathlib import Path
import subprocess
import shlex
from contextlib import chdir
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('ROS_DOMAIN_ID', 'ROS_AUTOMATIC_DISCOVERY_RANGE', 'RMW_IMPLEMENTATION',
        'CYCLONEDDS_URI', 'ROS_LOCALHOST_ONLY', 'ROS_STATIC_PEERS')


class SimulationEnvironmentTests(unittest.TestCase):
    def test_package_install_does_not_copy_python_cache_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'launch/__pycache__').mkdir(parents=True)
            (root/'launch/sim.launch.py').write_text('# launch fixture\n')
            setup = Mock()
            with chdir(root), patch.dict(sys.modules, {'setuptools': SimpleNamespace(setup=setup)}):
                runpy.run_path(str(ROOT/'ros2_ws/src/eyecar_sim/setup.py'))
            files = dict(setup.call_args.kwargs['data_files'])['share/eyecar_sim/launch']
            self.assertEqual(files, ['launch/sim.launch.py'])

    def test_switching_between_rover_and_simulation_clears_old_settings(self):
        env = dict(os.environ, ROS_DOMAIN_ID='0', ROS_AUTOMATIC_DISCOVERY_RANGE='SUBNET',
                   CYCLONEDDS_URI='file:///missing/rover.xml', ROS_LOCALHOST_ONLY='1',
                   ROS_STATIC_PEERS='192.168.50.1')
        report = 'python3 -c ' + shlex.quote(
            'import json,os; print(json.dumps({k:os.environ[k] for k in '+repr(KEYS)+' if k in os.environ}))')
        output = subprocess.check_output(
            ['bash', '-c', 'source "$1/deploy/ros-rover.bash"; '
             +report+'; source "$1/deploy/ros-sim.bash"; '+report,
             'bash', str(ROOT)], env=env, text=True)
        rover, sim = [json.loads(line) for line in output.splitlines()]
        self.assertEqual(rover['ROS_DOMAIN_ID'], '0')
        self.assertEqual(rover['ROS_AUTOMATIC_DISCOVERY_RANGE'], 'SUBNET')
        self.assertEqual(rover['CYCLONEDDS_URI'], (ROOT/'deploy/dds/laptop.xml').as_uri())
        self.assertEqual(sim['ROS_DOMAIN_ID'], '42')
        self.assertEqual(sim['ROS_AUTOMATIC_DISCOVERY_RANGE'], 'LOCALHOST')
        self.assertEqual(sim['RMW_IMPLEMENTATION'], 'rmw_cyclonedds_cpp')
        self.assertNotIn('CYCLONEDDS_URI', sim)
        for settings in (rover, sim):
            for key in ('ROS_LOCALHOST_ONLY', 'ROS_STATIC_PEERS'):
                self.assertNotIn(key, settings)


if __name__ == '__main__':
    unittest.main()
