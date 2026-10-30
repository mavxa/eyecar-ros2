# First boot and ROS 2 Jazzy

Target: Raspberry Pi 4 Model B, Ubuntu Server 24.04 LTS ARM64 and ROS 2 Jazzy.
Use the Raspberry Pi preinstalled server image from [Ubuntu's Pi downloads](https://ubuntu.com/download/raspberry-pi).
Keep a backup of the stock card before replacing it.

## Provision access before boot

Write the image with Raspberry Pi Imager or an equivalent image writer.
Provision your user and SSH public key through the image's supported first-boot
configuration. Do not copy a private key to the SD card or commit credentials.

Ubuntu Pi images use cloud-init. If you edit the boot partition's `user-data`
yourself, a minimal account configuration looks like this. Replace the public
key line with your actual `.pub` key and review the whole file before boot:

```yaml
#cloud-config
hostname: eyecar
users:
  - name: mavxa
    groups: [sudo, dialout, video]
    shell: /bin/bash
    lock_passwd: true
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    ssh_authorized_keys:
      - ssh-ed25519 REPLACE_WITH_YOUR_PUBLIC_KEY laptop
ssh_pwauth: false
```

This example uses key login and passwordless sudo for the provisioned account.
It does not create a usable password login. The service templates in this
repository use `/home/mavxa`; adapt them if you choose another account.

Keep Ethernet DHCP enabled in the boot partition's `network-config`:

```yaml
version: 2
ethernets:
  eth0:
    dhcp4: true
    optional: true
```

Connect Ethernet to a router LAN port. A direct laptop cable needs a DHCP
server on the laptop, such as Windows Internet Connection Sharing, or a
deliberate static-address setup. A cable alone does not assign an address.
Find the Pi in the router's leases, then connect with `ssh mavxa@PI_ADDRESS`.
If first boot cannot complete headlessly, use a USB keyboard and micro-HDMI
display, or correct the card's provisioning files from another Linux system.

On a running Ubuntu system, active Netplan files end in `.yaml`. Files ending
in `.bak` or `.disabled` are ignored. Keep an active Ethernet definition:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      optional: true
      dhcp4: true
```

Check and apply it with `sudo netplan generate` and `sudo netplan apply`.

## Check the Pi

On the Pi:

```bash
uname -m
cat /etc/os-release
ip -br address
sudo apt update
sudo apt full-upgrade
sudo reboot
```

Expect `aarch64`, Ubuntu 24.04 and an Ethernet address. Reconnect after reboot.

## Install Jazzy

The following commands run on the Pi. Ensure a UTF-8 locale and enable Universe:

```bash
sudo apt install locales curl software-properties-common
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository -y universe
```

Install the ROS apt-source package using the
[official Jazzy instructions](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html):

```bash
ROS_APT_SOURCE_VERSION=$(curl -fsSL \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F 'tag_name' | awk -F'"' '{print $4}')
curl -fL -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install ros-jazzy-ros-base ros-dev-tools ros-jazzy-rmw-cyclonedds-cpp
sudo rosdep init
rosdep update
```

If rosdep is already initialized, keep its existing sources and run
`rosdep update`. ROS is installed system-wide at `/opt/ros/jazzy`; each user
sources that installation and their own or the shared workspace.

```bash
source /opt/ros/jazzy/setup.bash
grep -qxF 'source /opt/ros/jazzy/setup.bash' ~/.bashrc \
  || echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
ros2 --help
```

## Get the deployment files

Keep a checkout on the Pi for firmware, service templates and examples:

```bash
sudo apt install git rsync
cd ~
git clone https://github.com/mavxa/eyecar-ros2.git
```

For an existing checkout, update the branch you are testing rather than cloning
again. The examples below use the SSH alias `eyecar`; configure it on the laptop
or substitute `mavxa@PI_ADDRESS` in SSH, SCP and rsync destinations.

## Build the Pi workspace

From the repository root on the laptop, copy only source files:

```bash
ssh eyecar 'mkdir -p ~/ros2_ws/src'
rsync -av ros2_ws/src/ eyecar:~/ros2_ws/src/
```

On the Pi:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Do not transfer laptop `build/` or `install/` directories to the ARM64 Pi.
Build them on the target. To load the Pi workspace in later Bash sessions:

```bash
grep -qxF 'source ~/ros2_ws/install/setup.bash' ~/.bashrc \
  || echo 'source ~/ros2_ws/install/setup.bash' >> ~/.bashrc
```

## USB access and next steps

Connect a Pi USB-A port to the Mega's USB-B data port:

```bash
lsusb
ls -l /dev/serial/by-id/
sudo usermod -aG dialout,video "$USER"
```

Log out and reconnect so new group membership takes effect. Identify the actual
serial device; the project defaults to a CH340 path. Continue with
[firmware upload](ROS_WORKFLOW_AND_FIRMWARE.md#mega-firmware) and
[Pi services](WEB_PANEL.md). Use [NETWORKING.md](NETWORKING.md) to add the AP
and enable direct laptop ROS access after the base installation works.
