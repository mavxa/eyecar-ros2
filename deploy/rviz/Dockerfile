FROM ros:jazzy-ros-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rviz2 ros-jazzy-robot-state-publisher ros-jazzy-tf2-ros python3-websocket \
    && rm -rf /var/lib/apt/lists/*

ENV QT_QPA_PLATFORM=xcb QT_X11_NO_MITSHM=1 \
    ROS_DOMAIN_ID=81 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

CMD ["bash", "/workspace/deploy/rviz/start.sh"]
