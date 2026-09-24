# eyecar_base

ROS 2 bridge between `/cmd_vel` and the EyeCar microcontroller.

The driver opens the persistent CH340 path and waits for the exact firmware
banner `READY EYECAR_BASE_V1`. It refuses to send any command to unknown
firmware. Physical motion is enabled by default; stale `/cmd_vel` commands are
replaced with zero after 0.5 seconds.

Standalone start, mainly for diagnostics:

```bash
ros2 run eyecar_base serial_driver
```

To disable physical output explicitly:

```bash
ros2 run eyecar_base serial_driver --ros-args \
  -p motion_enabled:=false
```

Protocol sent at 20 Hz:

```text
C <sequence> <throttle -1000..1000> <steering -1000..1000>
STOP
```

The controller must stop the motor if valid commands stop arriving.

For normal operation, this driver runs continuously as
`eyecar-base.service`. The keyboard publisher can be started and stopped
independently:

```bash
ros2 run eyecar_teleop keyboard_teleop
```

Service diagnostics:

```bash
systemctl --user status eyecar-base.service
journalctl --user -u eyecar-base.service -f
```

Current confirmed signal wiring on KvantoShield:

- motor controller signal: `S3` (microcontroller digital pin 3);
- steering servo signal: `S2` (microcontroller digital pin 2).

Use the `S/V/G` PLS connectors rather than moving the signal leads to the
separate `D` header. Confirm the power and ground rows before applying power.
