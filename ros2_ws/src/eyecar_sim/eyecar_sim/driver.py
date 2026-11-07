"""webots_ros2 plugin implementing the hardware-facing EyeCar ROS contracts."""
import json
import math
from pathlib import Path

import cv2
import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import CompressedImage, Image, JointState
from std_msgs.msg import ColorRGBA, UInt8, UInt16MultiArray
from tf2_ros import TransformBroadcaster

from eyecar_interfaces.msg import LedState, LedStateArray
from eyecar_interfaces.srv import SetLeds
from .control import WHEELS, ultrasonic_cm, wheel_commands


class EyeCarDriver:
    def init(self, webots_node, properties):
        self.robot = webots_node.robot
        if not rclpy.ok():
            rclpy.init(args=None)
        self.node = rclpy.create_node('eyecar_sim_driver')
        share = Path(get_package_share_directory('eyecar_sim'))
        self.d = json.loads((share / 'config/dimensions.json').read_text())
        self.period = int(self.robot.getBasicTimeStep())
        self.motors = [self.robot.getDevice(name+'_motor') for name in WHEELS]
        self.encoders = [self.robot.getDevice(name+'_encoder') for name in WHEELS]
        self.steering = [self.robot.getDevice(f'front_{side}_steer') for side in ('left', 'right')]
        self.steer_encoders = [self.robot.getDevice(f'front_{side}_steer_encoder') for side in ('left', 'right')]
        for motor in self.motors:
            motor.setPosition(float('inf'))
            motor.setVelocity(0)
        for motor in self.steering:
            motor.setPosition(0)
        self.us = [self.robot.getDevice('us_'+s['name']) for s in self.d['sensors']]
        self.ir = [self.robot.getDevice(f'ir_{i}') for i in range(5)]
        self.camera = self.robot.getDevice('camera')
        self.gps, self.imu = self.robot.getDevice('gps'), self.robot.getDevice('imu')
        for sensor in self.encoders+self.steer_encoders+self.us+self.ir+[self.camera, self.gps, self.imu]:
            sensor.enable(self.period)
        self.leds = [self.robot.getDevice(f'led_{i}') for i in range(13)]
        self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]*4+[(255, 0, 0)]
        self.brightness = 32
        self.linear = self.angular = 0.0
        self.received_at = -100.0
        self.last = dict(camera=-100.0, sensors=-100.0, pose=-100.0, leds=-100.0)
        self.previous_pose = None
        self.node.create_subscription(Twist, '/cmd_vel', self.command, 10)
        self.node.create_subscription(ColorRGBA, '/eyecar/led/color', self.color, 10)
        self.node.create_subscription(UInt8, '/eyecar/led/brightness', self.set_brightness, 10)
        self.node.create_service(SetLeds, '/eyecar/led/set_leds', self.set_leds)
        self.clock = self.node.create_publisher(Clock, '/clock', 10)
        self.ultrasonic = self.node.create_publisher(UInt16MultiArray, '/eyecar/ultrasonic', 10)
        self.infrared = self.node.create_publisher(UInt16MultiArray, '/eyecar/infrared', 10)
        self.raw = self.node.create_publisher(Image, '/camera/image_raw', qos_profile_sensor_data)
        self.jpeg = self.node.create_publisher(CompressedImage, '/camera/image_raw/compressed', qos_profile_sensor_data)
        self.joints = self.node.create_publisher(JointState, '/joint_states', 10)
        self.odometry = self.node.create_publisher(Odometry, '/simulation/odom', 10)
        self.tf = TransformBroadcaster(self.node)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.led_state = self.node.create_publisher(LedStateArray, '/eyecar/led/state', latched)
        self.brightness_state = self.node.create_publisher(UInt8, '/eyecar/led/brightness_state', latched)
        self.render_leds()

    def command(self, msg):
        self.linear, self.angular = msg.linear.x, msg.angular.z
        self.received_at = self.robot.getTime()

    def color(self, msg):
        values = (msg.r, msg.g, msg.b)
        if all(math.isfinite(v) for v in values):
            self.colors = [tuple(round(max(0, min(1, v))*255) for v in values)]*13
            self.render_leds()

    def set_brightness(self, msg):
        self.brightness = msg.data
        self.render_leds()

    def set_leds(self, request, response):
        if any(led.index >= 13 for led in request.leds):
            response.success = False
            response.message = 'Pixel index must be 0-12'
            return response
        for led in request.leds:
            self.colors[led.index] = (led.r, led.g, led.b)
        self.render_leds()
        response.success, response.message = True, 'Updated'
        return response

    def render_leds(self):
        for led, rgb in zip(self.leds, self.colors):
            r, g, b = (round(v*self.brightness/255) for v in rgb)
            led.set((r << 16) | (g << 8) | b)
        self.led_state.publish(LedStateArray(leds=[
            LedState(index=i, r=r, g=g, b=b) for i, (r, g, b) in enumerate(self.colors)]))
        self.brightness_state.publish(UInt8(data=self.brightness))

    def publish_camera(self, stamp):
        data = self.camera.getImage()
        if not data:
            return
        width, height = self.camera.getWidth(), self.camera.getHeight()
        frame = cv2.cvtColor(np.frombuffer(data, np.uint8).reshape(height, width, 4), cv2.COLOR_BGRA2BGR)
        image = Image(height=height, width=width, encoding='bgr8', step=width*3, data=frame.tobytes())
        image.header.stamp, image.header.frame_id = stamp, 'camera_optical_frame'
        self.raw.publish(image)
        ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            self.jpeg.publish(CompressedImage(header=image.header, format='jpeg', data=encoded.tobytes()))

    def publish_pose(self, stamp, now):
        joints = JointState()
        joints.header.stamp = stamp
        joints.name = [name+'_wheel_joint' for name in WHEELS] + ['front_left_steering', 'front_right_steering']
        joints.position = [s.getValue() for s in self.encoders+self.steer_encoders]
        if not all(math.isfinite(v) for v in joints.position):
            return
        self.joints.publish(joints)
        xyz = self.gps.getValues()
        yaw = self.imu.getRollPitchYaw()[2]
        if not all(math.isfinite(v) for v in (*xyz, yaw)):
            return
        odom = Odometry(child_frame_id='base_link')
        odom.header.stamp, odom.header.frame_id = stamp, 'sim_odom'
        p, q = odom.pose.pose.position, odom.pose.pose.orientation
        p.x, p.y, p.z = xyz
        q.z, q.w = math.sin(yaw/2), math.cos(yaw/2)
        if self.previous_pose:
            then, x, y, angle = self.previous_pose
            dt = now-then
            odom.twist.twist.linear.x = ((p.x-x)*math.cos(yaw)+(p.y-y)*math.sin(yaw))/dt
            odom.twist.twist.angular.z = math.atan2(math.sin(yaw-angle), math.cos(yaw-angle))/dt
        self.previous_pose = (now, p.x, p.y, yaw)
        self.odometry.publish(odom)
        transform = TransformStamped(header=odom.header, child_frame_id='base_link')
        transform.transform.translation.x, transform.transform.translation.y, transform.transform.translation.z = xyz
        transform.transform.rotation = q
        self.tf.sendTransform(transform)

    def step(self):
        for _ in range(4):
            rclpy.spin_once(self.node, timeout_sec=0)
        now = self.robot.getTime()
        ns = round(now*1e9)
        stamp = Time(sec=ns//1_000_000_000, nanosec=ns % 1_000_000_000)
        self.clock.publish(Clock(clock=stamp))
        fresh = now-self.received_at < self.d['command_timeout_s']
        speeds, angles = wheel_commands(self.linear if fresh else 0, self.angular if fresh else 0, self.d)
        for motor, speed in zip(self.motors, speeds):
            motor.setVelocity(speed)
        for motor, angle in zip(self.steering, angles):
            motor.setPosition(angle)
        if now-self.last['camera'] >= 0.1:
            self.publish_camera(stamp)
            self.last['camera'] = now
        if now-self.last['sensors'] >= 0.2:
            self.ultrasonic.publish(UInt16MultiArray(data=[ultrasonic_cm(s.getValue()) for s in self.us]))
            self.infrared.publish(UInt16MultiArray(data=[max(0, min(1023, round(s.getValue()))) for s in self.ir]))
            self.last['sensors'] = now
        if now-self.last['pose'] >= 0.05:
            self.publish_pose(stamp, now)
            self.last['pose'] = now
        if now-self.last['leds'] >= 1:
            self.render_leds()
            self.last['leds'] = now
