# RViz on the laptop

For an interactive container where you start RViz and nodes yourself, see
[DEVELOPMENT.md](DEVELOPMENT.md). Both modes build from the root Dockerfile.
For direct DDS reception without an SSH tunnel, see [NETWORKING.md](NETWORKING.md).
The commands below start the existing model and telemetry viewer automatically.

Run from a terminal in the laptop's graphical session, at the repository root:

```bash
bash scripts/eyecar-rviz build
bash scripts/eyecar-rviz
```

The first command builds an Ubuntu/ROS 2 Jazzy container with RViz. It downloads
the base image and packages. The second opens a dedicated SSH tunnel to the
`eyecar` SSH alias and starts RViz locally through XWayland with GPU access.
For a different SSH destination, use `bash scripts/eyecar-rviz user@address`.
Docker, XWayland, xauth, and working SSH authentication are required on the laptop.
If XWayland uses local-user authorization instead of cookies, xhost is also
required to check the existing permission.
No ROS packages are installed into CachyOS itself.

For an offline model preview with synthetic commands and sensors:

```bash
bash scripts/eyecar-rviz demo
```

Demo uses domain 84 and container `eyecar-rviz-demo`, with no SSH connection.
It can run alongside the normal viewer. All readings and motion are labelled
DEMO. An optional graphics fallback is
`LIBGL_ALWAYS_SOFTWARE=1 bash scripts/eyecar-rviz demo`.

The data path is:

```text
Pi ROS -> existing read-only panel bridge at 127.0.0.1:9090
       -> SSH tunnel at laptop 127.0.0.1:19090
       -> laptop container's rviz_bridge.py -> local ROS -> RViz
```

The existing bridge accepts only topic listing and watching. The receiver
only watches `/eyecar/ultrasonic`, `/eyecar/infrared` and `/cmd_vel`, then republishes
them inside local ROS domain 81. It sends no ROS publications or commands
to the Pi. The Pi's DDS loopback configuration and services remain unchanged.
The image uses `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`; host networking is
used to reach the SSH tunnel. Closing RViz stops the receiver and closes
the dedicated SSH connection. X11 authorization uses a temporary cookie
file or an existing local-user permission with the same UID in the container.
The launcher does not change global display permissions.

RViz starts with `command_odom` as its fixed frame and an orbit camera following
`base_link`. `robot_state_publisher` loads the generated URDF and publishes
the model/sensor transforms. The receiver publishes the steering and wheel
joint states. RViz displays the model, four distance arrows in the order
rear/right/left/front, text telemetry, and an orange command-derived path.
An ultrasonic zero means no echo: its arrow is deleted, rather than marking
the whole direction as free space. Arrows expire after one second without
fresh readings. Raw IR values are shown as ADC values, not as distances.

## What the movement means

`/cmd_vel` is a command, not feedback. EyeCar's base driver uses `linear.x` as
a throttle input and `angular.z` as a steering input. The display therefore
uses a nominal bicycle model with an estimated steering range to integrate
the command. Position, speed and steering angle are not measured values.
Wheel slip, acceleration, braking, battery state and actual servo calibration
are not modelled. The display stops integrating after 0.5 seconds without
fresh commands and does not rotate the car in place when speed is zero.

`/eyecar/command_estimate` is a display-only `nav_msgs/Odometry` in
`command_odom`; `/eyecar/command_path` is its bounded trajectory. These must
not be treated as measured `/odom` or fed to navigation as calibrated odometry.
The scene can move while the real rover is blocked or its motion is disabled.

Reset the display's origin and trajectory locally:

```bash
docker exec -it eyecar-rviz /ros_entrypoint.sh ros2 service call \
  /eyecar/reset_command_estimate std_srvs/srv/Empty '{}'
```

## Editing the model

Dimensions and sensor positions are in `models/eyecar/dimensions.json`, with
X forward, Y left, Z up. This is the active configuration; the old
`deploy/rviz/geometry.json` is retained only as a legacy reference.
Read `models/eyecar/README.md` for measured versus provisional dimensions.
The model is a visual assembly, not a measured collision footprint or fabrication CAD.

Edit the dimensions and restart the viewer. The launcher regenerates the URDF
and robot_state_publisher parameters in `/tmp/eyecar-model` on each launch.
Python and JSON edits need no Docker rebuild; rebuild if dependencies change.
For exported URDF, OpenSCAD, STL, DXF and image previews, run on the laptop:

```bash
python scripts/eyecar_model.py
```

Full export uses matplotlib on the laptop; the container's runtime-only export
uses the Python standard library. Outputs are in `models/eyecar/generated/`.
STL and CAD reference dimensions are in mm; URDF dimensions are in meters.

Inspect received topics from another laptop terminal:

```bash
docker exec -it eyecar-rviz /ros_entrypoint.sh ros2 topic echo /eyecar/ultrasonic
docker exec -it eyecar-rviz /ros_entrypoint.sh ros2 topic echo /eyecar/infrared
docker exec -it eyecar-rviz /ros_entrypoint.sh ros2 topic echo /cmd_vel
```

If there are no readings, inspect the receiver logs in the launch terminal
and verify `ssh eyecar` and `systemctl --user status eyecar-rosbridge` on Pi.
The WebSocket address is configurable with `EYECAR_BRIDGE_URL` when running
the Python receiver separately. It uses the EyeCar panel's custom `watch`
protocol, not the rosbridge_suite protocol.

For a later Nav2 costmap, add sensor_msgs/Range topics and measured sensor
transforms, then configure RangeSensorLayer. Odometry is needed to retain
a consistent map while the rover moves. The command estimate is not a substitute.

References: [ROS container images](https://hub.docker.com/_/ros),
[RViz marker display](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Intermediate/RViz/Marker-Display-types/Marker-Display-types.rst),
[Nav2 range layer](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/costmap_2d/costmap_plugins/range/).


## Home Ethernet check (31 October 2026)

The Pi was reachable through a home router at the time of this check. An SSH
forward to its loopback bridge returned the live topic catalogue and a live
`/rosout` message inside the development container. In a separate local domain,
RViz started with OpenGL 4.5, `robot_state_publisher` loaded the generated model,
and the receiver published `base_link` and wheel/steering transforms.

No Arduino USB serial device was present. Sensor readings, steering animation
from real commands and physical movement were therefore not verified. This
checks the SSH viewer path, not direct DDS over the AP. The AP-specific DDS
profile deliberately excludes the home Ethernet subnet; connect the laptop to
the rover AP for that workflow, or use the SSH viewer over Ethernet.
