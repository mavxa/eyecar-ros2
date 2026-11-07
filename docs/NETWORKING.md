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

## Pick the environment

| Work | Container | ROS domain / discovery | Network required |
| --- | --- | --- | --- |
| Webots, student nodes and RViz together | `eyecar-sim` | 42 / LOCALHOST | Laptop only; no AP or DDS XML |
| Student nodes and RViz with the real rover | `eyecar-ros2` | 0 / SUBNET, AP DDS XML | Laptop connected to the EyeCar AP |
| Legacy read-only SSH viewer | `eyecar-rviz` | 81 / LOCALHOST | SSH to the real rover; not a simulation client |

The simulator already includes RViz. A separate viewer container is optional,
not part of the normal simulation workflow. If using another ROS process on
the same Linux laptop, give it the same domain and discovery settings. Both
Compose configurations use host networking.

A **Wi-Fi connection profile** makes Linux join the AP. A **DDS profile**
chooses the interfaces used by ROS. `ROS_DOMAIN_ID` separates ROS graphs.
Changing the domain does not connect the laptop to Wi-Fi or assign an IP address.

## Create the laptop's EyeCar Wi-Fi profile

Run these commands on the **Linux laptop host**, outside Docker. This example
uses NetworkManager, as on CachyOS; the Pi instructions below use networkd.
Check for an existing `eyecar` connection with `nmcli connection show` first.
If it already exists, activate it instead of creating a duplicate.

```bash
nmcli device wifi list
nmcli --ask device wifi connect "ROStics-tehnopark33" name eyecar
nmcli connection modify eyecar connection.autoconnect no
```

Enter the AP password at the prompt. The connection is saved for later use,
but will not automatically replace your normal Wi-Fi. For subsequent sessions:

```bash
nmcli --ask connection up eyecar
ip -4 route get 192.168.50.1
ping -c 3 192.168.50.1
```

Expect an AP-subnet address on the laptop and a route through its Wi-Fi
interface. Open `http://192.168.50.1/`. This AP is local and need not provide
Internet access. A working panel proves IP reachability, not DDS discovery.
The desktop network settings can save the same profile without using nmcli.
See [NetworkManager examples](https://networkmanager.dev/docs/api/latest/nmcli-examples.html).

## Select the laptop's ROS profile

Inside the normal development container, Compose already sets the real-rover
profile. To select it explicitly, including after a simulation session:

```bash
source /workspace/deploy/ros-rover.bash
printenv ROS_DOMAIN_ID ROS_AUTOMATIC_DISCOVERY_RANGE RMW_IMPLEMENTATION
printf '%s\n' "$CYCLONEDDS_URI"
ros2 daemon stop
ros2 topic list
```

Expect domain `0`, `SUBNET`, `rmw_cyclonedds_cpp`, and a URI ending in
`deploy/dds/laptop.xml`. The script derives the XML path from its own location;
it also works as `source deploy/ros-rover.bash` from a native laptop checkout
with ROS installed. It clears legacy localhost/static-peer settings.

The checked-in XML files are the starting profiles: `laptop.xml` selects the
AP subnet `192.168.50.0/24` and loopback; `rover.xml` requires the Pi's AP
address `192.168.50.1`. If changing the AP subnet, update these addresses together.
No new XML needs to be written for the standard setup. Activate the Pi side
with the [one-time instructions](#one-time-pi-activation) below.

For simulation instead, source `/workspace/deploy/ros-sim.bash` in every
simulation/RViz/student-node shell. It selects domain `42`, `LOCALHOST` and
clears the rover XML. See [SIMULATION.md](SIMULATION.md). Stop and restart nodes
when switching environments. Do not source the laptop profile on the Pi:
the Pi services use the separate `rover.xml` deployment described below.

## Set up the Pi access point

Use Ethernet SSH for this step so changing Wi-Fi cannot disconnect your shell.
The AP is a local rover network; it does not share Internet access. Ethernet
keeps DHCP client mode, so plugging the Pi into a router still provides recovery
access. Download packages before switching Wi-Fi to AP mode.

```bash
sudo apt install hostapd iw rfkill
sudo cp -a /etc/netplan "/root/eyecar-netplan-$(date +%Y%m%d-%H%M%S)"
sudo mkdir -p /etc/cloud/cloud.cfg.d
printf 'network: {config: disabled}\n' | sudo tee /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
```

Inspect the active `/etc/netplan/*.yaml` files. Rename old Wi-Fi client files
with a `.disabled` suffix; Netplan ignores them. If a file also defines Ethernet,
preserve that part. Keep one Ethernet definition, for example
`/etc/netplan/70-eyecar-ethernet.yaml`:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      optional: true
      dhcp4: true
```

The interface names must match `ip -br link`. Give Wi-Fi its own networkd file,
`/etc/systemd/network/05-eyecar-ap.network`:

```ini
[Match]
Name=wlan0

[Link]
RequiredForOnline=no

[Network]
Address=192.168.50.1/24
ConfigureWithoutCarrier=yes
DHCPServer=yes
IPv6AcceptRA=no
LinkLocalAddressing=no

[DHCPServer]
PoolOffset=20
PoolSize=100
EmitDNS=no
EmitRouter=no
```

Here **networkd** supplies DHCP leases to AP clients. It is separate from the
Ethernet DHCP client. No second DHCP server such as dnsmasq is needed.

Create `/etc/hostapd/hostapd.conf` with the following content. Replace the password
placeholder with your own 8–63 character passphrase and set the country code to
your actual location. Do not commit the real password.

```ini
interface=wlan0
driver=nl80211
ssid=ROStics-tehnopark33
country_code=RU
ieee80211d=1
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=REPLACE_WITH_YOUR_PASSWORD
```

Apply from Ethernet SSH:

```bash
sudo chmod 600 /etc/netplan/*.yaml /etc/hostapd/hostapd.conf
sudo netplan generate
sudo netplan apply
sudo systemctl enable --now systemd-networkd
sudo networkctl reload
sudo networkctl reconfigure wlan0
sudo rfkill unblock wifi
sudo systemctl unmask hostapd
sudo systemctl enable --now hostapd
```

Check both the service and a real client:

```bash
iw dev wlan0 info
ip -4 -br address show wlan0
networkctl status wlan0
journalctl -u hostapd -n 30 --no-pager
```

Expect `type AP`, address `192.168.50.1/24`, and a visible SSID. A connected
phone/laptop should receive `192.168.50.20`–`192.168.50.119` and reach
`http://192.168.50.1/`. Check again after a reboot. An active hostapd process
without a visible SSID or a client lease is not a successful AP setup.

Multicast can work on this AP. The DDS profiles below use it for discovery,
while sending topic payloads over unicast. Both sides need the same domain and
reachable interfaces. Having an SSID alone does not configure ROS discovery.

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
if [ -f /opt/eyecar-vision/ros-local.env ]; then
  cp /opt/eyecar-vision/ros-local.env "$EYECAR_BACKUP/vision.env"
fi
printf 'Backup: %s\n' "$EYECAR_BACKUP"
sudo install -m 644 /tmp/eyecar-dds-ap.xml /home/mavxa/eyecar_web/cyclonedds-ap.xml
if [ -d /opt/eyecar-vision ]; then
  sudo install -m 644 /tmp/eyecar-dds-ap.xml /opt/eyecar-vision/cyclonedds-ap.xml
fi
```

Edit `/home/mavxa/eyecar_web/ros-local.env` with `nano`. Change these two lines,
leaving other settings intact:

```ini
ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
CYCLONEDDS_URI=file:///home/mavxa/eyecar_web/cyclonedds-ap.xml
```

If the optional shared vision environment is installed, edit
`/opt/eyecar-vision/ros-local.env` with `sudo nano`. Change:

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

Open a fresh shell that sources the active `~/eyecar_web/ros-local.env`,
or source it with `set -a; source ~/eyecar_web/ros-local.env; set +a`. Stop an old ROS CLI discovery daemon with `ros2 daemon stop` after changing
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

For a single command, run inside the development container:

```bash
bash /workspace/deploy/rviz/start.sh
```

This starts the model publisher, telemetry node and configured RViz together.
Plain `rviz2` does not start those nodes or load the EyeCar display settings.
Close the viewer before starting another model/telemetry instance.

To manage each process yourself, run these commands in separate container terminals:

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
