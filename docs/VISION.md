# Vision experiments on EyeCar

The Raspberry Pi has one shared Python environment for model inference:
`/opt/eyecar-vision/venv`. Both `mavxa` and `griftf` can run its Python.
Install or update dependencies as `mavxa`, not with system-wide `pip`.
The system ROS 2 Jazzy installation stays under `/opt/ros/jazzy`.

The trained model is a separate file. Copy the student's `best.pt` to
`/opt/eyecar-vision/models/best.pt` before testing. The model file is not
included in this repository.

To reproduce the shared setup on the Pi:

```bash
sudo apt install python3-venv
sudo install -d -o mavxa -g users -m 0755 /opt/eyecar-vision
sudo install -d -o mavxa -g users -m 2775 /opt/eyecar-vision/models
python3 -m venv --system-site-packages /opt/eyecar-vision/venv
/opt/eyecar-vision/venv/bin/python -m pip install \
  torch==2.9.0 torchvision==0.24.0 ultralytics==8.4.164 cffi
install -m 0644 deploy/vision-ros.env /opt/eyecar-vision/ros-local.env
install -m 0644 deploy/cyclonedds-loopback.xml \
  /opt/eyecar-vision/cyclonedds-loopback.xml
```

Run the setup as `mavxa`; both accounts may execute the installed interpreter.
Verify the imports after sourcing ROS:

```bash
source /opt/ros/jazzy/setup.bash
/opt/eyecar-vision/venv/bin/python -c \
  'import cv2, rclpy, torch, ultralytics; print(torch.__version__, ultralytics.__version__)'
/opt/eyecar-vision/venv/bin/python -m pip check
```

## Check the model on one image

From either user account on the Pi:

```bash
/opt/eyecar-vision/venv/bin/python - <<'PY'
from ultralytics import YOLO

model = YOLO('/opt/eyecar-vision/models/best.pt')
result = model.predict('/path/to/test.jpg', device='cpu', verbose=False)[0]
result.save(filename='/tmp/eyecar-detection.jpg')
print(result.boxes)
PY
```

## Example mission in `scripts/`

`scripts/modul1.py` uses the student's `best.pt` from
`griftf/eyecar-yolo/marked_dataset` in `/opt/eyecar-vision/models/best.pt`.
It drives forward until the model detects class `blue`, then stops and sets
the LED strip to light blue. Detection continues after stopping: both model
classes (`sticklight` and `blue`) appear in the annotated camera stream,
in `/camera/detections`, and in the console log.
It is a plain Python file; `colcon build` is not needed. Its camera ROS
interface is:

| Direction | Topic | Type |
| --- | --- | --- |
| Subscribe | `/camera/image_raw/compressed` | `sensor_msgs/msg/CompressedImage` |
| Publish | `/camera/annotated/compressed` | `sensor_msgs/msg/CompressedImage` |
| Publish | `/camera/detections` | `std_msgs/msg/String` containing JSON |

Each `/camera/detections` message contains the input frame's `stamp_ns` and a
`detections` array. Every detection has `class_id`, `class`, `confidence`, and
`bbox_xyxy` in pixels. The array is empty when nothing is detected.

The camera publisher already reads from the local RTSP stream, so the script
should subscribe to ROS rather than open `/dev/video0` again. Decode the input
JPEG with OpenCV, call `YOLO(best.pt).predict(frame)`, draw detections with
`result.plot()`, encode the output as JPEG, and publish it with the input
header and `format='jpeg'`. Keep only the newest input frame while CPU
inference is busy, so old frames do not queue up. Use sensor-data QoS when
subscribing. Start with `imgsz=416` and measure throughput on the Pi; change
it only after checking detection quality and CPU load.

Launch it from a shell with the ROS workspace and local DDS profile loaded:

```bash
source /opt/ros/jazzy/setup.bash
set -a; source /opt/eyecar-vision/ros-local.env; set +a
/opt/eyecar-vision/venv/bin/python /opt/eyecar-vision/scripts/modul1.py
```

Each user can keep a clone of this repository in their own home directory;
`/home/mavxa` is not traversable by `griftf`. The shared venv and model
directory remain accessible to both accounts. This script uses standard ROS
image messages, so the system ROS setup is enough; it does not need the
workspace under `/home/mavxa`.

When the script publishes JPEG messages, the panel automatically lists
`/camera/annotated/compressed` under **Cameras**. Open the topic page to see
the latest annotated frame. The panel's WebSocket bridge is read-only and
does not run the model. No browser or Nginx configuration is needed for this
topic. Check ROS first with:

```bash
ros2 topic info /camera/annotated/compressed
ros2 topic hz /camera/annotated/compressed
ros2 topic echo /camera/detections
```

The annotated topic exists only while `modul1.py` is running.
