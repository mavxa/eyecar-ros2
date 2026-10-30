# Ultrasonic and infrared sensors

The Mega sends `US c1 c2 c3 c4` and `IR a0 a1 a2 a3 a4` over USB serial at
115200 baud. `eyecar_base/serial_driver` is the only owner of that port.
It publishes a message when it receives a new valid sensor report.

| Topic | Type | Array order | Units |
| --- | --- | --- | --- |
| `/eyecar/ultrasonic` | `std_msgs/msg/UInt16MultiArray` | Rear, right, left, front | Centimetres; 0 means no echo |
| `/eyecar/infrared` | `std_msgs/msg/UInt16MultiArray` | A0, A1, A2, A3, A4 | Raw ADC, 0–1023 |

The directional ultrasonic mapping follows this project's installation.
Confirm it on your rover by holding an object in front of one module at a time.
See the [Mega pin table](Wiring.md#arduino-mega-signals) for TRIG/ECHO pairs.

The firmware triggers one HC-SR04 every 50 ms to reduce interference, reporting
all four after a complete cycle, about 5 Hz. Zero is not a zero-distance obstacle.
A valid echo can still be unreliable on angled or sound-absorbing surfaces.
The firmware's configured maximum range is 400 cm.

IR reports arrive nominally every 100 ms. The current sketch reads five analog
inputs. These values are not distances in centimetres. Check each module's AO
connection, surface response and supply rating before choosing a threshold.
The visual model has four IR boards; the firmware exposes five channels.
Their physical ordering has not been established from the photographs.

## Inspect the readings

On the Pi, source ROS, the workspace and the active DDS environment:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
set -a; source ~/eyecar_web/ros-local.env; set +a
ros2 topic echo /eyecar/ultrasonic
```

In another prepared shell:

```bash
ros2 topic echo /eyecar/infrared
ros2 topic hz /eyecar/ultrasonic
ros2 topic hz /eyecar/infrared
```

With [direct DDS networking](NETWORKING.md), the same ROS commands work inside
the laptop container. The read-only panel also shows both arrays.

No USB connection means no new readings. The driver retries the connection;
it does not repeat cached values as fresh measurements. An older sketch without
US/IR reports can complete the startup handshake while producing no sensor data.

## Service and motion settings

```bash
systemctl --user status eyecar-base.service
journalctl --user -u eyecar-base.service -n 30 --no-pager
systemctl --user cat eyecar-base.service
```

The checked-in service permits motion. A local systemd override may set
`motion_enabled:=false`; inspect the effective unit if commands are ignored.
Do not start a second serial driver or Arduino Serial Monitor alongside this
service. For a sensor-only bench session, stop teleop and other command publishers
before changing the driver's motion setting.

For visualisation, see [RViz](RVIZ.md). Four range sensors provide local obstacle
readings, not a lidar scan or a SLAM map.
