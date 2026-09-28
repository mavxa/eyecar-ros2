# eyecar_led

ROS 2 driver for a three-wire WS2812/SK6812-compatible strip connected to
BCM GPIO18, physical pin 12. The power supply and Raspberry Pi must share GND.

The EyeCar configuration controls 13 pixels at low brightness. On startup it
repeats red, green, blue across the strip. It supports a single fill color and
per-pixel updates.

## Install and build on the Raspberry Pi

```bash
sudo apt update
sudo apt install -y python3-rpi-ws281x ros-jazzy-rmw-cyclonedds-cpp

cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install \
  --packages-select eyecar_interfaces eyecar_led
source install/setup.bash
```

PWM control on GPIO18 normally needs root access:

```bash
sudo bash -lc '
  source /opt/ros/jazzy/setup.bash
  source /home/mavxa/ros2_ws/install/setup.bash
  ros2 run eyecar_led led_strip --ros-args \
    -p gpio_pin:=18 \
    -p led_count:=13 \
    -p brightness:=64
'
```

For normal operation, install and enable the included root system service. All
EyeCar ROS processes use the same loopback-only Cyclone DDS profile:

```bash
sudo install -m 0644 deploy/systemd/eyecar-led.service \
  /etc/systemd/system/eyecar-led.service
sudo systemctl daemon-reload
sudo systemctl enable --now eyecar-led.service
```

## Topics

Open a new SSH session after installing the DDS profile, or source it manually
in the current shell. Then publish a color:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
set -a; source ~/eyecar_web/ros-local.env; set +a
ros2 topic pub --once \
  /eyecar/led/color std_msgs/msg/ColorRGBA \
  "{r: 1.0, g: 0.0, b: 0.0, a: 1.0}"
```

Set brightness from 0 to 255:

```bash
ros2 topic pub --once \
  /eyecar/led/brightness std_msgs/msg/UInt8 \
  "{data: 64}"
```

Current values are published in `/eyecar/led/state` and
`/eyecar/led/brightness_state`. Publishing black turns the strip off.

The previous Fast DDS one-shot command discovered the root LED node without
delivering the color. The shared Cyclone DDS profile fixes that mismatch.

## Individual pixels

The `/eyecar/led/set_leds` service takes pixel indices 0–12 and RGB components
from 0 to 255. The example script sets all pixels in one service request:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
python3 ~/eyecar-ros2/examples/led_modes.py white
python3 ~/eyecar-ros2/examples/led_modes.py rgb
python3 ~/eyecar-ros2/examples/led_modes.py off
python3 ~/eyecar-ros2/examples/led_modes.py halves
```

`rgb` repeats red/green/blue. `halves` sets pixels 0–6 red and 7–12 blue.

This package assumes a WS2812/SK6812-compatible digital strip. Do not run it
against an analog RGB strip or a module with a different protocol.
