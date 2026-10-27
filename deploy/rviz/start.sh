#!/usr/bin/env bash
set -euo pipefail
python3 /workspace/scripts/eyecar_model.py --runtime-only --output-dir /tmp/eyecar-model
ros2 run robot_state_publisher robot_state_publisher \
    --ros-args --params-file /tmp/eyecar-model/robot_state_publisher.yaml &
model_pid=$!
python3 /workspace/scripts/rviz_bridge.py &
bridge_pid=$!
rviz2 -d /workspace/deploy/rviz/eyecar.rviz &
rviz_pid=$!
trap 'kill "$bridge_pid" "$rviz_pid" "$model_pid" 2>/dev/null || true; wait "$bridge_pid" "$rviz_pid" "$model_pid" 2>/dev/null || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
wait "$rviz_pid"
