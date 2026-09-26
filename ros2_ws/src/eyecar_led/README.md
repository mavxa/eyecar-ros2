# eyecar_led

ROS 2 driver for a three-wire WS2812/SK6812-compatible strip connected to
BCM GPIO18, physical pin 12. The power supply and Raspberry Pi must share GND.

The EyeCar configuration controls 12 pixels at low brightness. It supports a
single fill color and Clover-style per-pixel updates.

## Install and build on the Raspberry Pi

```bash
sudo apt update
sudo apt install -y python3-rpi-ws281x

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
    -p led_count:=12 \
    -p brightness:=64
'
```

For normal operation, install and enable the included root system service. It
forces Fast DDS to use UDP so non-root EyeCar nodes can communicate with the
root hardware driver:

```bash
sudo install -m 0644 deploy/systemd/eyecar-led.service \
  /etc/systemd/system/eyecar-led.service
sudo systemctl daemon-reload
sudo systemctl enable --now eyecar-led.service
```

## Topics

Set all pixels to red:

```bash
ros2 topic pub --once /eyecar/led/color std_msgs/msg/ColorRGBA \
  "{r: 1.0, g: 0.0, b: 0.0, a: 1.0}"
```

Set brightness from 0 to 255:

```bash
ros2 topic pub --once /eyecar/led/brightness std_msgs/msg/UInt8 \
  "{data: 64}"
```

Current values are published in `/eyecar/led/state` and
`/eyecar/led/brightness_state`. Publishing black turns the strip off.

## Individual pixels

The `/eyecar/led/set_leds` service follows the same model as Clover: each item
contains a pixel index and its RGB components from 0 to 255. Indices are 0–11.

Set the first half blue and the second half red:

```bash
ros2 service call /eyecar/led/set_leds eyecar_interfaces/srv/SetLeds "{
  leds: [
    {index: 0, r: 0, g: 0, b: 255},
    {index: 1, r: 0, g: 0, b: 255},
    {index: 2, r: 0, g: 0, b: 255},
    {index: 3, r: 0, g: 0, b: 255},
    {index: 4, r: 0, g: 0, b: 255},
    {index: 5, r: 0, g: 0, b: 255},
    {index: 6, r: 255, g: 0, b: 0},
    {index: 7, r: 255, g: 0, b: 0},
    {index: 8, r: 255, g: 0, b: 0},
    {index: 9, r: 255, g: 0, b: 0},
    {index: 10, r: 255, g: 0, b: 0},
    {index: 11, r: 255, g: 0, b: 0}
  ]
}"
```

This package assumes a WS2812/SK6812-compatible digital strip. Do not run it
against an analog RGB strip or a module with a different protocol.
