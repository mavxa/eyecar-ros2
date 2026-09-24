# EyeCar ROS 2

ROS 2 Jazzy software for an educational EyeCar rover based on Raspberry Pi 4
and Arduino Mega 2560.

```text
keyboard / web panel -> /cmd_vel -> serial driver -> Arduino -> motor + steering
USB camera -> ffmpeg -> MediaMTX -> WebRTC panel
```

## Structure

- `ros2_ws/src/` — ROS 2 packages;
- `firmware/` — Arduino firmware;
- `web/` — minimal browser panel;
- `deploy/` — MediaMTX and systemd user services;
- `docs/` — installation and workflow notes;
- `scripts/` — helper scripts.

Target: Ubuntu Server 24.04 ARM64 with ROS 2 Jazzy.

## Security status

The current web panel has no authentication or operator lock. Anyone who can
reach its network ports can publish rover control commands. Use it only on a
trusted isolated network until authentication and command ownership are added.

Licensed under the MIT License.
