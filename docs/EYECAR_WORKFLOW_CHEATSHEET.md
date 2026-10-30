# ROS 2 workflow

Use this guide to write a node yourself. The laptop container has ROS 2 Jazzy;
the Pi runs the hardware services. With [DDS networking](NETWORKING.md), a node
on either machine can subscribe to the same topics without being copied to the Pi.

## Package, executable and node

```mermaid
flowchart LR
    W[Workspace] --> P[Packages in src/]
    P --> E[Installed executables]
    E --> N[Running ROS nodes]
    N --> T[Topics and services]
```

`ros2 run eyecar_teleop keyboard_teleop` selects a package and its installed
executable. The Python entry point is listed in `setup.py`. The ROS node's name
comes from the code and can be different from both names.

A topic appears when a running node creates a publisher or subscription.
There is no separate topic-creation step. A workspace is a build directory,
not a network boundary. Matching domain, middleware, discovery settings, message
types and reachable interfaces determine which nodes can communicate.

## Start with a plain script

Create `scripts/hello_rover.py` in your own checkout:

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class HelloRover(Node):
    def __init__(self):
        super().__init__('hello_rover')
        self.publisher = self.create_publisher(String, '/eyecar/hello', 10)
        self.create_timer(1.0, self.send)

    def send(self):
        self.publisher.publish(String(data='Hello from the laptop'))


def main():
    rclpy.init()
    node = HelloRover()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
```

Inside the development container:

```bash
cd /workspace
source /opt/ros/jazzy/setup.bash
python3 scripts/hello_rover.py
```

In a second container terminal:

```bash
ros2 node list
ros2 topic info /eyecar/hello
ros2 topic echo /eyecar/hello
```

The timer sends a typed message once per second. A subscriber uses
`create_subscription(String, '/eyecar/hello', callback, 10)` to receive it.
For camera input use sensor-data QoS, as in the existing camera/vision examples.

## Turn the script into a package executable

Run from the repository workspace in the container:

```bash
cd /workspace/ros2_ws/src
ros2 pkg create --build-type ament_python --dependencies rclpy std_msgs -- rover_examples
cp /workspace/scripts/hello_rover.py rover_examples/rover_examples/hello_rover.py
```

In the generated `rover_examples/setup.py`, add this entry under
`entry_points['console_scripts']`:

```python
'hello_rover = rover_examples.hello_rover:main',
```

Then build and source the overlay:

```bash
cd /workspace/ros2_ws
colcon build --symlink-install --packages-select rover_examples
source install/setup.bash
ros2 run rover_examples hello_rover
```

`--symlink-install` makes most Python edits visible without rebuilding. Rebuild
when entry points, package metadata or installed resources change. Source the
overlay in each new shell. Do not copy the laptop's `build/` or `install/` to ARM64.

## Run a node at Pi boot

First copy the package sources to `~/ros2_ws/src` on the Pi and build there.
Test the executable manually. Create a user unit at
`~/.config/systemd/user/rover-hello.service`, replacing `mavxa` if needed:

```ini
[Unit]
Description=Rover hello example
After=network.target

[Service]
EnvironmentFile=/home/mavxa/eyecar_web/ros-local.env
ExecStart=/bin/bash -c 'source /opt/ros/jazzy/setup.bash && source /home/mavxa/ros2_ws/install/setup.bash && exec ros2 run rover_examples hello_rover'
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```

Enable it as that user:

```bash
systemctl --user daemon-reload
systemctl --user enable --now rover-hello.service
sudo loginctl enable-linger "$USER"
journalctl --user -u rover-hello.service -n 30 --no-pager
```

This keeps the node running without an open SSH session. A script alone is not
installed into a package by `colcon`: its package metadata and entry point are
what make `ros2 run` find it.

## Hardware and firmware

`/cmd_vel` carries normalised driver inputs in this build, not calibrated
physical velocity. Start with the existing teleop settings. Running several
command publishers at once makes control unpredictable.

Use [firmware workflow](ROS_WORKFLOW_AND_FIRMWARE.md) for Mega compilation and
upload, [sensor reference](SENSORS.md) for array ordering, and
[LED examples](../examples/led_modes.py) for whole-strip and per-pixel changes.

References: [Python publisher/subscriber](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html),
[creating a package](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html).
