# Nodes, packages and Mega firmware

## Python file or ROS executable

A script that imports `rclpy` can run with `python3 scripts/my_node.py` after
loading ROS and its dependencies. Packaging is useful for installation,
dependencies, launch files and `ros2 run`; it is not required just to create
a publisher.

For an `ament_python` package, `setup.py` maps an executable name to a function:

```python
entry_points={
    'console_scripts': [
        'keyboard_teleop = eyecar_teleop.keyboard_teleop:main',
    ],
}
```

This gives `ros2 run eyecar_teleop keyboard_teleop`. The first name is the
package, the second is the executable, and the code chooses the ROS node name
inside `Node(...)`. See the [worked Python example](EYECAR_WORKFLOW_CHEATSHEET.md).

Inside the laptop container, rebuild an existing package with:

```bash
cd /workspace/ros2_ws
colcon build --symlink-install --packages-select eyecar_teleop
source install/setup.bash
ros2 run eyecar_teleop keyboard_teleop
```

On the Pi the workspace is `~/ros2_ws`. Source `/opt/ros/jazzy/setup.bash`
and the active DDS profile there. The shared Pi environment, when installed,
is loaded with `source /opt/eyecar-vision/ros-env.bash`.

## Mega firmware

Arduino firmware is built with Arduino CLI, independently of colcon. The
target is `arduino:avr:mega:cpu=atmega2560`. The laptop compiles a `.hex`; the
Pi can upload that file over its USB connection to the Mega. Nothing in this
procedure requires copying an x86 Python environment to the Pi.

Install Arduino CLI from its [official instructions](https://arduino.github.io/arduino-cli/latest/installation/).
On the laptop, prepare the AVR core and libraries:

```bash
arduino-cli core update-index
arduino-cli core install arduino:avr
arduino-cli lib install Servo NewPing
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 \
  --warnings all --output-dir /tmp/eyecar-fw firmware/eyecar_base_controller
scp /tmp/eyecar-fw/eyecar_base_controller.ino.hex eyecar:/tmp/
```

The current source uses NewPing for four HC-SR04 modules and Servo for the
motor/steering pulses. See [Wiring.md](Wiring.md) before moving signal leads.

On the Pi, Arduino CLI and the AVR core must also be available for upload.
Inspect `arduino-cli board list` and `/dev/serial/by-id/` to identify the port.
The base service owns that port, so stop it before uploading. Keep the wheels
lifted for this maintenance step:

```bash
systemctl --user stop eyecar-base.service
arduino-cli upload --verify --fqbn arduino:avr:mega:cpu=atmega2560 \
  --port /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 \
  --input-file /tmp/eyecar_base_controller.ino.hex
systemctl --user start eyecar-base.service
journalctl --user -u eyecar-base.service -n 30 --no-pager
```

That port is the reference build's CH340 path. Substitute your actual device.
Do not open a serial monitor while the ROS driver is running. If upload fails,
restore a known firmware and check the handshake before running teleop.

## Serial contract

The link is USB serial at 115200 baud, with newline-terminated ASCII messages.
The controller announces `READY EYECAR_BASE_V1`. The driver waits for this
banner before sending commands.

```text
Pi -> Mega: C <sequence> <throttle -1000..1000> <steering -1000..1000>
Pi -> Mega: STOP
Mega -> Pi: ACK <sequence> <motor_us> <steering_us>
Mega -> Pi: US <rear_cm> <right_cm> <left_cm> <front_cm>
Mega -> Pi: IR <A0> <A1> <A2> <A3> <A4>
```

The firmware also reports malformed commands and watchdog stops. Its command
timeout is 400 ms; the ROS driver replaces stale commands after 0.5 seconds.
These stop stale input. They do not measure stopping distance.

## Pulse calibration and command meaning

| Setting | Current firmware value |
| --- | --- |
| Motor neutral | 1500 microseconds |
| Full forward command | 1630 microseconds |
| Full reverse command | 1350 microseconds |
| Steering center | 1500 microseconds |
| Steering range | 1300-1700 microseconds |
| Reverse sequence | 180 ms brake, 180 ms neutral, then reverse |

The ROS adapter divides `linear.x` by 0.25 for throttle and `angular.z` by
0.85 for steering, then clamps both to -1..1. Despite the `Twist` message
type, these are not calibrated vehicle velocity and yaw-rate commands.
Match the semantics explicitly when integrating a simulator or navigation
controller. A firmware pulse change also changes the real vehicle response.
