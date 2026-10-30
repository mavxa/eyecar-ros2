import ipaddress
import json
from pathlib import Path
import subprocess

ROOT = str(Path(__file__).resolve().parents[1])
NETWORK = 'eyecar-dds-check'
NAMES = ['eyecar-dds-rover-check', 'eyecar-dds-laptop-check']
SUBNET = ipaddress.ip_network('192.168.50.0/24')
routes = json.loads(subprocess.check_output(['ip', '-j', '-4', 'route', 'show']))
assert not any(ipaddress.ip_network(r['dst']).overlaps(SUBNET)
               for r in routes if r.get('dst', 'default') != 'default'), 'Disconnect the rover AP before testing'
for kind, name in [('network', NETWORK), ('container', NAMES[0]), ('container', NAMES[1])]:
    assert subprocess.run(['docker', kind, 'inspect', name], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0, f'{name} already exists'

created = []
network_created = False
try:
    subprocess.run(['docker', 'network', 'create', '--subnet', str(SUBNET),
                    '--gateway', '192.168.50.254', NETWORK], check=True, stdout=subprocess.DEVNULL)
    network_created = True
    for name, address, profile in zip(NAMES, ['192.168.50.1', '192.168.50.20'], ['rover', 'laptop']):
        subprocess.run(['docker', 'run', '-d', '--init', '--name', name, '--network', NETWORK,
                        '--ip', address, '-e', 'PYTHONUNBUFFERED=1', '-e', 'ROS_DOMAIN_ID=88',
                        '-e', 'ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET',
                        '-e', f'CYCLONEDDS_URI=file:///workspace/deploy/dds/{profile}.xml',
                        '-v', ROOT + ':/workspace:ro', 'eyecar-ros2:jazzy'],
                       check=True, stdout=subprocess.DEVNULL)
        created.append(name)
    for sender, receiver, label in [(NAMES[1], NAMES[0], 'laptop_to_rover'),
                                    (NAMES[0], NAMES[1], 'rover_to_laptop')]:
        topic = '/eyecar/network_probe_' + label
        listener = subprocess.Popen(['docker', 'exec', receiver, '/ros_entrypoint.sh',
                                     'ros2', 'topic', 'echo', topic, 'std_msgs/msg/String', '--once'],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            sent = subprocess.run(['docker', 'exec', sender, '/ros_entrypoint.sh', 'ros2', 'topic',
                                   'pub', '--once', topic, 'std_msgs/msg/String', '{data: ' + label + '}'],
                                  capture_output=True, text=True, timeout=25)
            assert sent.returncode == 0, sent.stdout + sent.stderr
            output = listener.communicate(timeout=10)[0]
            assert listener.returncode == 0 and 'data: ' + label in output, output
            print('PASS:', label, flush=True)
        finally:
            if listener.poll() is None:
                listener.terminate()
                try:
                    listener.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    listener.kill()
                    listener.communicate()
finally:
    for name in reversed(created):
        subprocess.run(['docker', 'stop', '-t', '2', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['docker', 'rm', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if network_created:
        subprocess.run(['docker', 'network', 'rm', NETWORK], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
