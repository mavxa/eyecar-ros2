# Build guide

This guide turns the existing EyeCar chassis into a ROS 2 system. Keep the
stock hardware where it works: the Mega remains responsible for pulse timing
and sensor polling, and the Pi provides Linux, ROS, networking and video.

The reference build has a Raspberry Pi 4 Model B with 8 GB RAM, Arduino Mega
2560, EyeCar expansion board, pulse-controlled motor driver, steering servo,
four HC-SR04 modules, five analog IR inputs, a USB camera and a 13-pixel strip.
The [photographs](Gallery.md) show the assembled rover. The
[wiring reference](Wiring.md) gives the software's pin assignments.

## Before replacing the software

Save the stock microSD image and any controller firmware you need to recover.
Store backups outside Git. Identify the board and power hardware rather than
relying on the chassis name alone. The repository targets a Mega 2560, not an
Uno, and the motor output is a servo-style pulse signal.

Prepare a Linux laptop with Git and Docker, a microSD writing method, a USB
data cable for the Mega and an Ethernet connection for initial Pi setup.
A monitor is optional if you provision SSH and DHCP before first boot.

## Installation path

| Step | Guide | Check before continuing |
| --- | --- | --- |
| 1. Inspect wiring and power | [Wiring](Wiring.md) | Correct supply voltage, common GND, Mega signal pins |
| 2. Boot Ubuntu / enable SSH | [First start](ROS2_FIRST_START.md) | Pi gets an Ethernet lease and accepts your SSH key |
| 3. Install Jazzy / build packages | [First start](ROS2_FIRST_START.md#install-jazzy) | `ros2` works and the workspace builds |
| 4. Compile and upload firmware | [Firmware workflow](ROS_WORKFLOW_AND_FIRMWARE.md#mega-firmware) | Driver receives `READY EYECAR_BASE_V1` |
| 5. Install Pi services and video | [Panel and services](WEB_PANEL.md) | Services run, camera has one capture owner, panel opens |
| 6. Create the rover AP / enable DDS | [Networking](NETWORKING.md) | Client receives an AP lease and sees fresh ROS messages |
| 7. Develop from the laptop | [Development container](DEVELOPMENT.md) | Python imports ROS and the laptop can exchange topics |
| 8. Inspect sensors and model | [Sensors](SENSORS.md), [RViz](RVIZ.md) | Each sensor channel has a known physical position |

Install packages while the Pi has internet through Ethernet. The rover AP is
a local network; its configuration does not share an internet connection.

## Choose the DDS mode

The web-service templates start with a loopback-only DDS profile. That supports
SSH-based operation and keeps ROS discovery on the Pi. The direct AP profile
allows laptop nodes to read topics and publish commands. Pick the latter for
the laptop workflow in this repository and apply it once after service setup.

All participating processes must use the same domain and compatible DDS
settings, including the root LED service. Workspace directory names do not
control discovery. Do not overwrite an active AP profile with the loopback
template when updating the panel.

## First verification

Start with the wheels lifted. Check the serial handshake and sensor values
before opening a control node. The base service is the only serial-port owner;
close Arduino serial monitors before starting it. Then check forward, reverse,
steering and the stop timeout separately. Pulse limits are specific to the
installed driver and servo.

On the AP, open `http://192.168.50.1/` from the laptop and phone. Run a small
test publisher/subscriber before moving an autonomous node from simulation
or the laptop to the rover. Test discovery again after a Pi reboot.

The [workflow cheatsheet](EYECAR_WORKFLOW_CHEATSHEET.md) walks through a first
Python node. [VISION.md](VISION.md) covers the shared inference environment and
annotated camera topics. [Gallery.md](Gallery.md) contains every project photo
and the generated model views and downloads.

## What still needs measurement

The firmware pin map is explicit. Physical IR channel order, battery/ESC power
routing, wheel speed, steering angle, wheelbase and some CAD dimensions need
checks on the actual build. The command-based RViz animation does not replace
encoders or measured odometry. Camera latency, Wi-Fi throughput and inference
speed depend on the connected devices and model.
