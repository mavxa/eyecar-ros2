FROM ros:jazzy-ros-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rviz2 ros-jazzy-robot-state-publisher ros-jazzy-tf2-ros \
    ros-jazzy-rmw-cyclonedds-cpp python3-websocket python3-venv nano \
    && rm -rf /var/lib/apt/lists/*

ARG USER_UID=1000
ARG USER_GID=1000
RUN if ! getent group "$USER_GID" >/dev/null; then groupmod -g "$USER_GID" ubuntu; fi \
    && usermod -u "$USER_UID" -g "$USER_GID" ubuntu \
    && mkdir -p /home/ubuntu/.zed_server \
    && chown -R "$USER_UID:$USER_GID" /home/ubuntu \
    && printf 'ubuntu ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

RUN printf '\nsource /opt/ros/jazzy/setup.bash\nif [ -f /workspace/ros2_ws/install/setup.bash ]; then source /workspace/ros2_ws/install/setup.bash; fi\n' \
    >> /etc/bash.bashrc

ENV QT_QPA_PLATFORM=xcb QT_X11_NO_MITSHM=1 \
    ROS_DOMAIN_ID=0 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

USER ubuntu
WORKDIR /workspace
CMD ["sleep", "infinity"]
