# Direct ROS 2 through the rover AP

The development container can exchange ROS topics and services directly with
the Pi. SSH and the read-only WebSocket bridge are not part of this data path:

```text
laptop nodes in Docker <-> CycloneDDS / rover Wi-Fi AP <-> Pi nodes <-> Arduino
```

The AP is `ROStics-tehnopark33`, with the Pi at `192.168.50.1/24`.
Both machines use Jazzy, CycloneDDS and domain `0`. The profiles in `deploy/dds/`
select only this subnet and loopback. They do not advertise ROS on the Pi's
Ethernet connection or the laptop's other networks. Discovery uses multicast;
topic data uses unicast, which avoids multicasting camera frames over Wi-Fi.

The container side is configured in `compose.yaml`. The Pi needs the one-time
activation below. Preparing these files on the laptop does not activate the Pi.

## One-time Pi activation

Connect the laptop to the AP first. From the repository on the laptop, copy
the rover profile and open a shell on the Pi. Use the Pi's AP address if your
SSH alias points to an old Ethernet address. Run these commands on the laptop
host, outside the container; SSH keys stay on the laptop:

```bash
scp -o HostName=192.168.50.1 -o HostKeyAlias=eyecar.local deploy/dds/rover.xml eyecar:/tmp/eyecar-dds-ap.xml
ssh -o HostName=192.168.50.1 -o HostKeyAlias=eyecar.local eyecar
```

The following commands run on the Pi. Save the existing environment files:

```bash
EYECAR_BACKUP="$HOME/eyecar-dds-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$EYECAR_BACKUP"
cp /home/mavxa/eyecar_web/ros-local.env "$EYECAR_BACKUP/web.env"
cp /opt/eyecar-vision/ros-local.env "$EYECAR_BACKUP/vision.env"
printf 'Backup: %s\n' "$EYECAR_BACKUP"
sudo install -m 644 /tmp/eyecar-dds-ap.xml /home/mavxa/eyecar_web/cyclonedds-ap.xml
sudo install -m 644 /tmp/eyecar-dds-ap.xml /opt/eyecar-vision/cyclonedds-ap.xml
```

Edit `/home/mavxa/eyecar_web/ros-local.env` with `nano`. Change these two lines,
leaving other settings intact:

```ini
ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
CYCLONEDDS_URI=file:///home/mavxa/eyecar_web/cyclonedds-ap.xml
```

Edit `/opt/eyecar-vision/ros-local.env` with `sudo nano`. Change:

```ini
ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
CYCLONEDDS_URI=file:///opt/eyecar-vision/cyclonedds-ap.xml
```

Keep `ROS_DOMAIN_ID=0` and `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in both files.
If either file has `ROS_LOCALHOST_ONLY=1`, remove that setting.

Check that the AP address is present before restarting nodes:

```bash
ip -4 -br address show wlan0
systemctl --user restart eyecar-base eyecar-rosbridge eyecar-camera
sudo systemctl try-restart eyecar-led.service
```

The rover profile requires the AP address. Existing systemd services retry on
failure, so they can start after the AP becomes ready. This startup sequence
must also be checked after a real reboot. The hardware driver cannot provide
real readings without Arduino and its attached modules.

Open a fresh shell or source `/opt/eyecar-vision/ros-env.bash` in the existing
shell. Stop an old ROS CLI discovery daemon with `ros2 daemon stop` after changing
the profile. The web panel remains read-only and keeps its loopback WebSocket
listener; this change enables direct DDS access for AP clients.

To roll back, restore `web.env` and `vision.env` from the printed backup directory
to their original locations and restart the same services. The original
`cyclonedds-loopback.xml` files remain available.

## Daily laptop workflow

1. Connect Linux to the rover's AP using your normal Wi-Fi settings.
2. Start/open the development container in Zed, or use `docker compose up -d`
   followed by `docker exec -it eyecar-ros2 bash`.
3. Run your nodes in container terminals. They communicate with the Pi directly.

Check discovery in the container:

```bash
ros2 daemon stop
ros2 node list
ros2 topic list
ros2 topic echo /eyecar/ultrasonic --once
```

Run a script or the teleop package built in this workspace:

```bash
python3 scripts/my_node.py
ros2 run eyecar_teleop keyboard_teleop
```

The laptop profile allows loopback-only development without the AP. After
connecting to a different network, restart already-running nodes and the ROS
CLI daemon so DDS selects the new interface. DDS does not connect Linux to
Wi-Fi, and this setup does not cross unrelated networks or the internet.

## RViz with the rover model

In the development container, `EYECAR_RVIZ_DIRECT=1` makes `rviz_bridge.py`
subscribe directly to the Pi's ultrasonic, infrared and command topics. It
publishes only derived markers, joint states, TF and a command-based path.
It does not republish `/cmd_vel` or sensor inputs, preventing a feedback loop.
Your own nodes access other ROS topics directly without this viewer process.

Run these commands in separate container terminals:

```bash
# Terminal 1: model and fixed transforms.
python3 scripts/eyecar_model.py --runtime-only --output-dir /tmp/eyecar-model
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args --params-file /tmp/eyecar-model/robot_state_publisher.yaml
```

```bash
# Terminal 2: telemetry visualization and approximate joint/motion animation.
python3 scripts/rviz_bridge.py
```

```bash
# Terminal 3: viewer.
rviz2 -d /workspace/deploy/rviz/eyecar.rviz
```

Run one model/telemetry publisher set per rover domain. Additional users can
open RViz and subscribe to those outputs. The animated path is still an
estimate from commands, not measured odometry.

## Validation limits

With the laptop disconnected from the real rover AP, run the isolated Docker
network check on the laptop:

```bash
python3 tests/dds_network_integration.py
```

The test uses domain 88, two disposable containers and a temporary bridge on
the AP subnet. It refuses to run when that subnet is already in use and removes
its containers and network afterwards. It exchanges test strings in both
directions without publishing control commands.

Virtual-network tests can validate discovery and messages in both directions,
and offline tests can validate the viewer without publishing motor commands.
Real AP multicast, camera throughput, firewall behavior and persistence after
a Pi reboot need the Pi to be connected. Do not treat virtual tests as a
successful physical-rover check.

References: [DDS interface selection](https://cyclonedds.io/docs/cyclonedds/latest/config/network_interfaces.html),
[DDS configuration](https://cyclonedds.io/docs/cyclonedds/latest/config/config_file_reference.html).
