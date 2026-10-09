#!/usr/bin/env python3
import json
import threading
import time

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import ColorRGBA, String
from ultralytics import YOLO


MODEL = '/opt/eyecar-vision/models/best.pt'
SPEED = 0.18


class Modul1(Node):
    def __init__(self):
        super().__init__('modul1')
        self.model = YOLO(MODEL)
        self.model.predict(np.zeros((416, 416, 3), dtype=np.uint8), imgsz=416, verbose=False)
        self.latest_image = None
        self.last_image_at = 0.0
        self.detected = False
        self.error = False
        self.reported = False
        self.running = True

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.led_pub = self.create_publisher(ColorRGBA, '/eyecar/led/color', 10)
        self.image_pub = self.create_publisher(
            CompressedImage, '/camera/annotated/compressed', 10
        )
        self.detections_pub = self.create_publisher(String, '/camera/detections', 10)
        self.create_subscription(
            CompressedImage,
            '/camera/image_raw/compressed',
            self.on_image,
            qos_profile_sensor_data,
        )
        self.create_timer(0.1, self.on_timer)
        self.worker = threading.Thread(target=self.detect)
        self.worker.start()

    def on_image(self, message):
        self.latest_image = message
        self.last_image_at = time.monotonic()

    def on_timer(self):
        command = Twist()
        if self.detected:
            self.led_pub.publish(ColorRGBA(r=0.0, g=0.75, b=1.0, a=1.0))
            if not self.reported:
                self.get_logger().info('Blue stick detected: stopped, LEDs blue')
                self.reported = True
        elif not self.error and time.monotonic() - self.last_image_at < 1.0:
            command.linear.x = SPEED
        self.cmd_pub.publish(command)

    def detect(self):
        try:
            while rclpy.ok() and self.running:
                message = self.latest_image
                self.latest_image = None
                if message is None:
                    time.sleep(0.02)
                    continue

                frame = cv2.imdecode(np.frombuffer(message.data, np.uint8), cv2.IMREAD_COLOR)
                result = self.model.predict(frame, conf=0.3, imgsz=416, verbose=False)[0]
                detections = [
                    {
                        'class_id': int(box.cls.item()),
                        'class': result.names[int(box.cls.item())],
                        'confidence': round(float(box.conf.item()), 3),
                        'bbox_xyxy': [round(float(value)) for value in box.xyxy[0]],
                    }
                    for box in result.boxes
                ]
                self.detections_pub.publish(String(data=json.dumps({
                    'stamp_ns': message.header.stamp.sec * 1_000_000_000
                                + message.header.stamp.nanosec,
                    'detections': detections,
                })))
                if detections:
                    self.get_logger().info('Detections: ' + ', '.join(
                        f"{item['class']} conf={item['confidence']:.3f} "
                        f"bbox={item['bbox_xyxy']}" for item in detections
                    ))
                if any(item['class'] == 'blue' for item in detections):
                    self.detected = True

                jpeg = cv2.imencode('.jpg', result.plot())[1]
                self.image_pub.publish(CompressedImage(
                    header=message.header, format='jpeg', data=jpeg.tobytes()
                ))
        except Exception as exc:
            self.error = True
            self.get_logger().error(f'Detection failed: {exc}')


def main():
    rclpy.init()
    node = Modul1()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.running = False
        node.worker.join()
        if rclpy.ok():
            node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
