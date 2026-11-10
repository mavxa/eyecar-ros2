# EyeCar images

## Raspberry Pi microSD

Download `eyecar-vX.Y.Z-raspi-arm64.img.xz` and `SHA256SUMS` from the
[releases page](https://github.com/mavxa/eyecar-ros2/releases). From the
download directory on Linux, run `sha256sum -c SHA256SUMS`. In balenaEtcher,
choose **Flash from file**, select the compressed image and write it to
the microSD card. Use a card of at least 16 GB.

The image builds on Ubuntu Server 24.04 ARM64 for Raspberry Pi. It includes
ROS 2 Jazzy, the EyeCar workspace, the read-only panel, MediaMTX and the
system services. Use the release notes to check which boards passed a
physical boot test. Pi 4B and Pi 3B/3B+ are targets for the same image.

Before booting the Pi, reinsert the card on your computer and edit
`user-data` on the FAT boot partition. Put your **public** SSH key in the
existing Ubuntu user entry:

```yaml
    ssh_authorized_keys:
      - ssh-ed25519 AAAA... your-laptop
```

Use Ethernet with DHCP for the first boot, or configure Wi-Fi in
`network-config` on the same partition. The default user has a locked password
and SSH accepts keys. After cloud-init finishes, connect with
`ssh ubuntu@eyecar.local` or use the IP shown by the router.

Open the panel at `http://eyecar.local/`. From the Pi SSH shell:

```bash
source /etc/eyecar/ros-local.env
source /opt/ros/jazzy/setup.bash
source /opt/eyecar/install/setup.bash
ros2 topic list
systemctl status eyecar-base eyecar-video eyecar-camera eyecar-rosbridge eyecar-led
```

The ROS graph initially uses loopback. The service user has USB serial
and video access. See [Networking](NETWORKING.md) for setting up the rover AP,
and [firmware setup](ROS_WORKFLOW_AND_FIRMWARE.md#mega-firmware) for programming
the Mega. The firmware source ships under `/opt/eyecar/firmware`. Check the
actual serial path if the board uses a USB ID other than the default CH340.
The image leaves vision training and inference dependencies optional.

## Laptop container images

Download the images from GHCR using the version from the same release
as your checkout. On first publication, the repository owner needs to
make the two packages public in their package settings for anonymous pulls.

```bash
docker pull ghcr.io/mavxa/eyecar-ros2:0.1.0
docker pull ghcr.io/mavxa/eyecar-webots:0.1.0
```

To use the development image with Compose, export
`EYECAR_ROS_IMAGE=ghcr.io/mavxa/eyecar-ros2:0.1.0`, then run
`docker compose up -d` from the graphical Linux terminal. For the simulator,
export `EYECAR_SIM_IMAGE=ghcr.io/mavxa/eyecar-webots:0.1.0`, then use the
appropriate Compose command in [Simulation](SIMULATION.md). The same
`linux/amd64` simulator image works on Linux and Docker Desktop with
Ubuntu WSL2. Build the ROS simulation overlay inside the container as usual.

## Cut a release

Merge the workflow into `main` and wait for the build checks to pass.
Create and push an annotated version tag from that commit:

```bash
git switch main
git pull --ff-only
git tag -a v0.1.0 -m "EyeCar v0.1.0"
git push origin v0.1.0
```

The [EyeCar images workflow](../.github/workflows/release-images.yml) builds
the SD image on an ARM64 runner and attaches it with its checksum to a draft
release. The AMD64 job tests the simulation and pushes the two versioned
containers to GHCR. Relevant pushes to `dev` and `main` run the same build
checks without publishing. Published GitHub Releases have a 2 GiB limit per
asset, so the SD build checks the compressed size before uploading.

Before publishing the draft, check the workflow result and boot a card on
each board you intend to list as supported. Verify DHCP and SSH, the Arduino
handshake, panel, camera and sensor topics. Check that both GHCR versions can
be pulled. Record the tested hardware in the release notes.

For a local image build, use an ARM64 Linux machine with `cloud-guest-utils`,
`zerofree`, `e2fsprogs`, `xz-utils` and Bun installed. Build the panel with
`bun install --frozen-lockfile` and `bun run build` in `web/`, then run
`sudo scripts/build-sd-image v0.1.0 ./dist` from a committed checkout.
The script uses loop devices and temporary mounts to modify a fresh download
of the Ubuntu image.
