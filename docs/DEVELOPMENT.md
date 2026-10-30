# ROS 2 development container

The repository contains the Dockerfile and container configuration. Docker stores
the built image in its own storage; there is no image directory to enter.

This environment targets Linux with Docker Compose and X11 or XWayland. It has
Ubuntu 24.04, ROS 2 Jazzy, RViz, CycloneDDS, colcon, Python 3.12 and venv support.
The container stays running without starting RViz, rover nodes or an SSH tunnel.

## Start and enter

Run in a terminal on the laptop, at the repository root:

```bash
cd ~/zed/ros2/eyecar/eyecar-ros2
docker build -t eyecar-ros2:jazzy .
docker compose up -d
docker exec -it eyecar-ros2 bash
```

Inside the container, ROS is sourced automatically in interactive Bash:

```bash
rviz2
ros2 topic list
python3 scripts/my_node.py
```

`/workspace` is the mounted repository. Edits are immediately visible on the
laptop. The container does not contain files outside the repository.

For a second shell, run `docker exec -it eyecar-ros2 bash` in another terminal.
`exit` closes a shell; it does not stop the container. Stop it with
`docker compose down` from the repository on the laptop.

The default container user is `ubuntu`, UID/GID 1000, with sudo inside the
container. If your host IDs differ, use these build arguments from Bash:

```bash
docker build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) \
  -t eyecar-ros2:jazzy .
docker compose up -d --force-recreate
```

Avoid building a workspace as root: build products are written to the laptop's
mounted repository. Installed OS packages live in the container and are lost
when it is recreated; add lasting dependencies to the Dockerfile and rebuild.

## Build packages

Inside the container:

```bash
cd /workspace/ros2_ws
colcon build --symlink-install --packages-select eyecar_teleop
source install/setup.bash
ros2 run eyecar_teleop cmd_vel_monitor
```

New interactive shells automatically source this workspace after it is built.
Use the explicit source command after rebuilding in the current shell.

## RViz and the model

`rviz2` opens an empty viewer. Its displays receive whatever ROS publishers are
running in the selected domain. Loading a saved RViz configuration does not
start those publishers.

For example, to load the model manually, run this in one container shell:

```bash
python3 scripts/eyecar_model.py --runtime-only --output-dir /tmp/eyecar-model
ros2 run robot_state_publisher robot_state_publisher \
  --ros-args --params-file /tmp/eyecar-model/robot_state_publisher.yaml
```

In another container shell, run `rviz2`, set **Fixed Frame** to `base_link`, and
add **RobotModel** with **Description Topic** `/robot_description`. Wheel and
steering transforms need JointState messages. The existing viewer with
command-derived motion and telemetry is documented in [RVIZ.md](RVIZ.md).

Compose uses CPU rendering so it does not require host GPU devices or groups.
Start Compose from your graphical terminal so it inherits `DISPLAY`.
If your session uses an X11 cookie, export its path as `XAUTHORITY` before
starting the container. When that variable is unset, the container relies on
the X server's existing local-user authorization. If it rejects the window,
authorize only your own local user on the laptop:

```bash
xhost +si:localuser:$(id -un)
```

Do not use `xhost +`. To remove the local-user authorization after use:

```bash
xhost -si:localuser:$(id -un)
```

## Zed

Open the repository in Zed and choose **Open in Container**, or use
**Project: Open Remote** and **Connect Dev Container**. The configuration in
`.devcontainer/devcontainer.json` builds the image and uses the same Compose
service. If you already started it manually, stop it with `docker compose down` before the first
devcontainer connection, so the editor can create its managed instance.

Select `/usr/bin/python3` as the Python toolchain inside the container.
`pyrightconfig.json` supplies the ROS import path for basedpyright/Pyright.
Source paths for additional custom packages may need to be added there after
those packages are built. The configuration also works with other editors that
support Compose devcontainers.

The container remains running when the editor disconnects. Use `docker ps` to
find it and `docker exec -it eyecar-ros2 bash` to enter it manually.
Zed does not automatically rebuild a devcontainer after configuration changes;
recreate it when the Dockerfile or container settings change.

The Zed remote server is cached in a named Docker volume mounted at
`/home/ubuntu/.zed_server`. It survives container recreation and
`docker compose down`. The first connection, and connections after a Zed
update, still require downloading the matching server. Avoid
`docker compose down --volumes` if you want to keep this cache.

If `cloud.zed.dev` is unavailable, the matching server can be downloaded from
the [official Zed releases](https://github.com/zed-industries/zed/releases).
For Zed 1.25.3 on x86-64 Linux, run on the laptop with the container running:

```bash
curl -fL https://github.com/zed-industries/zed/releases/download/v1.25.3/zed-remote-server-linux-x86_64.gz \
  -o /tmp/zed-remote-server.gz
gzip -dc /tmp/zed-remote-server.gz | docker exec -i eyecar-ros2 sh -c \
  'cat > /home/ubuntu/.zed_server/zed-remote-server-stable-1.25.3 && chmod 755 /home/ubuntu/.zed_server/zed-remote-server-stable-1.25.3'
docker exec eyecar-ros2 /home/ubuntu/.zed_server/zed-remote-server-stable-1.25.3 version
```

Use the version matching your editor and the asset matching the container's
architecture. Reconnect from Zed after installing it.

## Network and the Pi

Compose uses the host network, domain `0`, `SUBNET` discovery and CycloneDDS.
Its DDS profile selects the rover AP subnet `192.168.50.0/24` and loopback.
Connect the laptop to the rover AP for direct communication through that AP.
For another domain, set it when creating the container:

```bash
ROS_DOMAIN_ID=86 docker compose up -d
```

The Pi must use the same domain and allow discovery on its AP interface.
See [NETWORKING.md](NETWORKING.md) for the one-time Pi activation and manual
RViz workflow. These local files do not change the Pi's loopback-only profile.
The previous SSH/RViz viewer remains available independently.

References: [Docker's ROS 2 guide](https://docs.docker.com/guides/ros2/),
[Zed devcontainers](https://zed.dev/docs/dev-containers),
[Zed Python](https://zed.dev/docs/languages/python).


## Check a change

The host-side model, motion, wiring and documentation checks use Python's
standard library:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/eyecar_wiring.py --check
```

The ROS integration scripts must run in a sourced Jazzy environment. Keep them
in isolated test domains, away from the rover's command domain. The DDS network
integration creates and removes two disposable Docker containers; it refuses
to run while the AP subnet is already routed on the laptop.

```bash
python3 tests/dds_network_integration.py
```

None of these host checks validates real motor motion or sensor accuracy.
