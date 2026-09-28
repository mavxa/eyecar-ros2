"""Publish frames from MediaMTX RTSP without opening the USB camera twice."""

from __future__ import annotations

import os
import threading

os.environ.setdefault('OPENCV_FFMPEG_CAPTURE_OPTIONS', 'rtsp_transport;tcp')
import cv2
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image


class CameraPublisher(Node):
    def __init__(self) -> None:
        super().__init__('eyecar_camera')
        self.declare_parameter('rtsp_url', 'rtsp://127.0.0.1:8554/cam')
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('jpeg_quality', 70)
        self.raw = self.create_publisher(Image, '/camera/image_raw', qos_profile_sensor_data)
        self.compressed = self.create_publisher(
            CompressedImage, '/camera/image_raw/compressed', qos_profile_sensor_data)
        self.lock = threading.Lock()
        self.frame = None
        self.frame_number = 0
        self.published_number = 0
        self.stopping = threading.Event()
        threading.Thread(target=self._capture_loop, daemon=True).start()
        fps = max(1.0, min(float(self.get_parameter('fps').value), 30.0))
        self.create_timer(1.0 / fps, self._publish_frame)

    def _capture_loop(self) -> None:
        url = str(self.get_parameter('rtsp_url').value)
        while not self.stopping.is_set():
            capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if not capture.isOpened():
                self.get_logger().warning('Camera RTSP unavailable; retrying')
                capture.release()
                self.stopping.wait(2.0)
                continue
            self.get_logger().info('Camera RTSP connected')
            try:
                while not self.stopping.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        break
                    with self.lock:
                        self.frame = frame
                        self.frame_number += 1
            finally:
                capture.release()
            self.stopping.wait(1.0)

    def _publish_frame(self) -> None:
        with self.lock:
            if self.frame is None or self.frame_number == self.published_number:
                return
            frame = self.frame.copy()
            self.published_number = self.frame_number
        height, width = frame.shape[:2]
        stamp = self.get_clock().now().to_msg()
        raw = Image()
        raw.header.stamp = stamp
        raw.header.frame_id = 'camera'
        raw.height = height
        raw.width = width
        raw.encoding = 'bgr8'
        raw.is_bigendian = False
        raw.step = width * 3
        raw.data = frame.tobytes()
        self.raw.publish(raw)
        quality = max(1, min(int(self.get_parameter('jpeg_quality').value), 95))
        ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            compressed = CompressedImage()
            compressed.header = raw.header
            compressed.format = 'jpeg'
            compressed.data = encoded.tobytes()
            self.compressed.publish(compressed)

    def stop(self) -> None:
        self.stopping.set()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CameraPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
