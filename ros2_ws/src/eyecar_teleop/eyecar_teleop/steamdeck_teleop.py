"""Receive normalized gamepad JSON on SSH stdin and publish ROS Twist."""

from __future__ import annotations

import math
import os
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from .gamepad_control import GamepadControl


class SteamDeckTeleop(Node):
    def __init__(self, node_name='steamdeck_teleop',
                 topic_parameter='output_topic', default_topic='/cmd_vel_test'):
        super().__init__(node_name)
        defaults = {
            'forward_speed': 0.18, 'reverse_speed': 0.25,
            'angular_speed': 0.85, 'command_timeout': 0.4,
            'deadzone': 0.12, 'publish_rate': 20.0,
            topic_parameter: default_topic,
        }
        for name, default in defaults.items():
            self.declare_parameter(name, default)
        self.forward = float(self.get_parameter('forward_speed').value)
        self.reverse = float(self.get_parameter('reverse_speed').value)
        self.angular = float(self.get_parameter('angular_speed').value)
        rate = float(self.get_parameter('publish_rate').value)
        for value in (self.forward, self.reverse, self.angular, rate):
            if not math.isfinite(value) or value <= 0:
                raise ValueError('speeds and publish_rate must be positive and finite')
        self.control = GamepadControl(
            float(self.get_parameter('command_timeout').value),
            float(self.get_parameter('deadzone').value))
        topic = str(self.get_parameter(topic_parameter).value)
        self.publisher = self.create_publisher(Twist, topic, 1)
        self.fd = sys.stdin.fileno()
        self.original_blocking = os.get_blocking(self.fd)
        os.set_blocking(self.fd, False)
        self.buffer = b''
        self.eof = False
        self.timer = self.create_timer(1 / rate, self.tick)
        self.get_logger().info(
            f'SSH gamepad -> {topic}; release enable with centered sticks to arm')

    def read_input(self):
        if self.eof:
            return
        try:
            data = os.read(self.fd, 65536)
        except BlockingIOError:
            return
        if not data:
            self.eof = True
            self.control.stop()
            return
        self.buffer += data
        if len(self.buffer) > 8192:
            self.buffer = b''
            self.control.stop()
            return
        while b'\n' in self.buffer:
            line, _, self.buffer = self.buffer.partition(b'\n')
            if len(line) > 512 or not self.control.receive(line, time.monotonic()):
                self.control.stop()
                self.get_logger().warning('Invalid gamepad packet; stopped')
        if len(self.buffer) > 512:
            self.buffer = b''
            self.control.stop()

    def publish_command(self, throttle=0.0, steering=0.0):
        message = Twist()
        message.linear.x = throttle * (self.forward if throttle >= 0 else self.reverse)
        message.angular.z = steering * self.angular
        self.publisher.publish(message)

    def tick(self):
        self.read_input()
        self.publish_command(*self.control.command(time.monotonic()))


def main(args=None, **node_options):
    rclpy.init(args=args)
    node = None
    try:
        node = SteamDeckTeleop(**node_options)
        while rclpy.ok() and not node.eof:
            rclpy.spin_once(node, timeout_sec=0.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            if rclpy.ok():
                node.publish_command()
                rclpy.spin_once(node, timeout_sec=0.05)
            os.set_blocking(node.fd, node.original_blocking)
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
