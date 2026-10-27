# EyeCar ROS 2

ROS 2 Jazzy software for an educational EyeCar rover based on Raspberry Pi 4
and Arduino Mega 2560.

```text
keyboard over SSH -> /cmd_vel -> serial driver -> Arduino -> motor + steering
USB camera -> ffmpeg -> MediaMTX -> WebRTC panel
                                -> RTSP -> eyecar_camera -> /camera/image_raw
```

## Structure

- `ros2_ws/src/` — ROS 2 packages;
- `firmware/` — Arduino firmware;
- `web/` — Vite-based read-only topic and camera browser;
- `deploy/` — Nginx, MediaMTX, local DDS profile, and systemd services;
- `docs/` — installation and workflow notes;
- `scripts/` — helper scripts.
- `examples/` — small ROS 2 usage examples, including LED colors.
- `models/eyecar/` — editable rover model and downloadable URDF/CAD exports.

Target: Ubuntu Server 24.04 ARM64 with ROS 2 Jazzy.

## Model and RViz

![EyeCar visual model](models/eyecar/generated/eyecar%20preview.png)

The model includes two 240 x 120 mm plates, wheels, electronics, four HC-SR04
sensors at the electronics level, a bumper with four IR modules, and a camera
centered in its holder. Dimensions come from measurements and photographs;
unmeasured mounts and chassis details remain approximate.

[Model files and dimensions](models/eyecar/README.md) ·
[URDF](models/eyecar/generated/eyecar.urdf) ·
[STL, mm](models/eyecar/generated/eyecar.stl) ·
[DXF drawing, mm](models/eyecar/generated/eyecar%20drawing.dxf)

On a Linux laptop with Docker and XWayland:

```bash
bash scripts/eyecar-rviz build
bash scripts/eyecar-rviz demo  # offline preview with synthetic data
bash scripts/eyecar-rviz       # live read-only telemetry through SSH to eyecar
```

RViz shows sonar readings, joint animation and a path estimated from `/cmd_vel`.
The path is not measured odometry. See [RVIZ.md](docs/RVIZ.md) for setup and
[SENSORS.md](docs/SENSORS.md) for the ultrasonic/IR topic contract.

## Security status

The deployed panel is read-only: its WebSocket bridge does not publish control
commands and listens on loopback behind Nginx. ROS services are configured for
local-only DDS; discovery from another ROS host has not yet been tested.
The camera and topic values remain visible to devices on the same network.

See [WEB_PANEL.md](docs/WEB_PANEL.md) for local preview and deployment, and
[ROS_WORKFLOW_AND_FIRMWARE.md](docs/ROS_WORKFLOW_AND_FIRMWARE.md) for ROS and
Arduino workflows. See [VISION.md](docs/VISION.md) for the shared Ultralytics
environment and the student's annotated-camera topic interface.

Licensed under the MIT License.
