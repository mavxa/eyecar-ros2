#!/usr/bin/env bash
# Run inside the mounted Ubuntu ARM64 image.
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8

printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
trap 'rm -f /usr/sbin/policy-rc.d' EXIT

dpkg -i /tmp/eyecar-ros-apt.deb
apt-get update
apt-get install -y --no-install-recommends \
    avahi-daemon build-essential cmake ffmpeg nginx openssh-server \
    python3-colcon-common-extensions python3-opencv python3-rpi-ws281x python3-serial \
    ros-jazzy-ros-base ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-rosidl-default-generators

useradd --system --create-home --home-dir /var/lib/eyecar --shell /usr/sbin/nologin \
    --groups dialout,video eyecar

cd /opt/eyecar
# ROS setup scripts can reference optional unset environment variables.
source /opt/ros/jazzy/setup.bash
export CMAKE_BUILD_PARALLEL_LEVEL=2
colcon build --base-paths ros2_ws/src --executor sequential --packages-skip eyecar_sim
rm -rf build log ros2_ws/src/eyecar_sim

install -d /etc/eyecar /var/www/eyecar
install -m 644 deploy/cyclonedds-loopback.xml deploy/mediamtx.yml /etc/eyecar/
sed 's|/home/mavxa/eyecar_web/|/etc/eyecar/|g' deploy/ros-local.env > /etc/eyecar/ros-local.env
install -m 755 /tmp/eyecar-mediamtx /usr/local/bin/mediamtx
cp -a web/dist/. /var/www/eyecar/
rm -r web/dist
install -m 644 deploy/nginx/eyecar.conf /etc/nginx/sites-available/eyecar
ln -sfn /etc/nginx/sites-available/eyecar /etc/nginx/sites-enabled/eyecar
rm -f /etc/nginx/sites-enabled/default

for template in deploy/systemd-user/*.service deploy/systemd/*.service; do
    unit="/etc/systemd/system/${template##*/}"
    sed -e 's|/home/mavxa/ros2_ws/install/|/opt/eyecar/install/|g' \
        -e 's|/home/mavxa/eyecar_web|/etc/eyecar|g' \
        -e 's|/home/mavxa/.local/bin/mediamtx|/usr/local/bin/mediamtx|g' \
        -e 's|WantedBy=default.target|WantedBy=multi-user.target|' \
        "$template" > "$unit"
    if [[ $template == deploy/systemd-user/* ]]; then
        sed -i '/^\[Service\]$/a User=eyecar' "$unit"
    fi
    systemctl --root=/ enable "${unit##*/}"
done

systemctl --root=/ enable ssh.service avahi-daemon.service nginx.service
nginx -t
systemd-analyze verify /etc/systemd/system/eyecar-*.service
source /opt/eyecar/install/setup.bash
python3 -c 'import cv2, rclpy, rpi_ws281x, serial; from eyecar_interfaces.msg import LedState'
ros2 pkg executables | grep '^eyecar_'
mediamtx --version

apt-get clean
rm -rf /var/lib/apt/lists/*
cloud-init clean --logs --machine-id
rm -f /etc/ssh/ssh_host_*
