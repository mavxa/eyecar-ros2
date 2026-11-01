FROM eyecar-ros2:jazzy

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates xvfb xauth python3-opencv \
    ros-jazzy-webots-ros2-driver \
    && curl -fL --retry 3 \
       https://github.com/cyberbotics/webots/releases/download/R2025a/webots_2025a_amd64.deb \
       -o /tmp/webots.deb \
    && apt-get install -y --no-install-recommends /tmp/webots.deb \
    && rm -f /tmp/webots.deb && rm -rf /var/lib/apt/lists/*

ENV WEBOTS_HOME=/usr/local/webots
USER ubuntu
