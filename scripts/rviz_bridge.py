#!/usr/bin/env python3
"""View EyeCar telemetry, URDF joints and explicitly command-derived motion locally."""

import json
import math
import os
from contextlib import closing
from pathlib import Path
import threading
import time

import rclpy
from geometry_msgs.msg import Point, PoseStamped, TransformStamped, Twist
from nav_msgs.msg import Odometry, Path as RosPath
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import UInt16MultiArray
from std_srvs.srv import Empty
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray
import websocket

from eyecar_motion import CommandEstimate


ROOT = Path(__file__).resolve().parents[1]
TOPIC_TYPES = {'/eyecar/ultrasonic': UInt16MultiArray,
               '/eyecar/infrared': UInt16MultiArray, '/cmd_vel': Twist}
TOPICS = tuple(TOPIC_TYPES)


def vector_fields(value):
    return {axis: float(getattr(value, axis)) for axis in ('x', 'y', 'z')}


class TelemetryBridge(Node):
    def __init__(self):
        super().__init__('eyecar_rviz_bridge')
        self.geometry = json.loads((ROOT / 'models/eyecar/dimensions.json').read_text())
        self.url = os.environ.get('EYECAR_BRIDGE_URL', 'ws://127.0.0.1:19090')
        self.publishers_by_topic = {
            topic: self.create_publisher(kind, topic, 10) for topic, kind in TOPIC_TYPES.items()
        }
        self.markers = self.create_publisher(MarkerArray, '/eyecar/ultrasonic_markers', 10)
        self.telemetry = self.create_publisher(MarkerArray, '/eyecar/telemetry_markers', 10)
        self.joints = self.create_publisher(JointState, '/joint_states', 10)
        self.odometry = self.create_publisher(Odometry, '/eyecar/command_estimate', 10)
        self.path_publisher = self.create_publisher(RosPath, '/eyecar/command_path', 10)
        self.transforms = TransformBroadcaster(self)
        self.motion = CommandEstimate(self.geometry)
        self.path = RosPath()
        self.path.header.frame_id = 'command_odom'
        self.last_path_at = 0.0
        self.sensor_values = {TOPICS[0]: None, TOPICS[1]: None}
        self.sensor_times = {}
        self.demo = os.environ.get('EYECAR_RVIZ_DEMO') == '1'
        self.started_at = time.monotonic()
        self.create_service(Empty, '/eyecar/reset_command_estimate', self.reset_estimate)
        self.latest = {}
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.workers = [] if self.demo else [threading.Thread(target=self.receive, args=(topic,)) for topic in TOPICS]
        for worker in self.workers:
            worker.start()
        self.create_timer(0.05, self.publish_latest)
        self.get_logger().info('DEMO: all readings and motion are synthetic' if self.demo else
                               'Receiving telemetry only; motion is a command estimate, not measured odometry')

    def receive(self, topic):
        # The existing panel bridge watches one topic per WebSocket connection.
        while not self.stopping.is_set():
            try:
                with closing(websocket.create_connection(self.url, timeout=2)) as connection:
                    connection.send(json.dumps({'op': 'watch', 'topic': topic}))
                    while not self.stopping.is_set():
                        try:
                            payload = connection.recv()
                        except websocket.WebSocketTimeoutException:
                            continue
                        if not payload:
                            break
                        event = json.loads(payload)
                        if event.get('op') == 'error':
                            raise ValueError(event.get('message', 'Bridge rejected watch'))
                        if event.get('op') == 'message' and event.get('topic') == topic:
                            message = event['msg']
                            if topic == '/cmd_vel':
                                values = [message[axis][coordinate] for axis in ('linear', 'angular')
                                          for coordinate in ('x', 'y', 'z')]
                                if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
                                    raise ValueError('Invalid velocity command')
                            else:
                                values = message['data']
                                count = 4 if topic == TOPICS[0] else 5
                                maximum = 400 if topic == TOPICS[0] else 1023
                                if len(values) != count or any(
                                    type(value) is not int or not 0 <= value <= maximum
                                    for value in values
                                ):
                                    raise ValueError('Invalid sensor readings')
                            with self.lock:
                                self.latest[topic] = (message, time.monotonic())
            except (OSError, ValueError, KeyError, TypeError, websocket.WebSocketException) as exc:
                if not self.stopping.is_set():
                    self.get_logger().warning(f'{topic}: {exc}; reconnecting')
            self.stopping.wait(2)

    def publish_latest(self):
        now = time.monotonic()
        with self.lock:
            latest, self.latest = self.latest, {}
        if self.demo:
            elapsed = now-self.started_at
            command = Twist()
            command.linear.x = 0.12 if elapsed % 18 < 14 else 0.0
            command.angular.z = 0.36 if elapsed % 18 > 5 else 0.0
            latest['/cmd_vel'] = ({'linear': vector_fields(command.linear), 'angular': vector_fields(command.angular)}, now)
            latest[TOPICS[0]] = ({'data': [75, 110, 130, int(80+25*math.sin(elapsed))]}, now)
            latest[TOPICS[1]] = ({'data': [200, 400, 300, 500, 0]}, now)
        for topic, (payload, received_at) in latest.items():
            if topic == '/cmd_vel':
                message = Twist()
                for axis in ('linear', 'angular'):
                    for coordinate in ('x', 'y', 'z'):
                        setattr(getattr(message, axis), coordinate, float(payload[axis][coordinate]))
                self.motion.set_command(message.linear.x, message.angular.z, received_at)
            else:
                message = UInt16MultiArray(data=payload['data'])
                self.sensor_values[topic] = list(message.data)
                self.sensor_times[topic] = received_at
                if topic == TOPICS[0]:
                    self.markers.publish(self.make_markers(message.data))
            self.publishers_by_topic[topic].publish(message)
        fresh = self.motion.step(now)
        self.publish_motion(now, fresh)

    def make_markers(self, values):
        stamp = self.get_clock().now().to_msg()
        result = MarkerArray()
        for index, (sensor, distance) in enumerate(zip(self.geometry['sensors'], values)):
            arrow = Marker()
            arrow.header.frame_id = 'base_link'
            arrow.header.stamp = stamp
            arrow.ns, arrow.id, arrow.type = 'ultrasonic', index, Marker.ARROW
            arrow.pose.orientation.w = 1.0
            arrow.action = Marker.ADD if distance else Marker.DELETE
            angle = math.radians(sensor['yaw_deg'])
            arrow.points = [
                Point(x=sensor['x'], y=sensor['y'], z=sensor['z']),
                Point(x=sensor['x'] + distance / 100 * math.cos(angle),
                      y=sensor['y'] + distance / 100 * math.sin(angle), z=sensor['z']),
            ]
            arrow.scale.x, arrow.scale.y, arrow.scale.z = 0.008, 0.025, 0.025
            arrow.color.r, arrow.color.g, arrow.color.b, arrow.color.a = 0.1, 0.7, 0.4, 1.0
            arrow.lifetime.sec = 1
            result.markers.append(arrow)
        return result

    def publish_motion(self, now, fresh):
        stamp = self.get_clock().now().to_msg()
        motion = self.motion
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'command_odom', 'base_link'
        transform.header.stamp = stamp
        transform.transform.translation.x, transform.transform.translation.y = motion.x, motion.y
        transform.transform.rotation.z = math.sin(motion.yaw/2)
        transform.transform.rotation.w = math.cos(motion.yaw/2)
        self.transforms.sendTransform(transform)

        joints = JointState()
        joints.header.stamp = stamp
        joints.name = ['front_left_steering', 'front_right_steering',
                       'front_left_wheel_joint', 'front_right_wheel_joint',
                       'rear_left_wheel_joint', 'rear_right_wheel_joint']
        joints.position = [*motion.steering_angles(), *([motion.wheel_angle]*4)]
        self.joints.publish(joints)

        odometry = Odometry()
        odometry.header, odometry.child_frame_id = transform.header, 'base_link'
        odometry.pose.pose.position.x, odometry.pose.pose.position.y = motion.x, motion.y
        odometry.pose.pose.orientation = transform.transform.rotation
        odometry.twist.twist.linear.x, odometry.twist.twist.angular.z = motion.speed, motion.yaw_rate
        # This is a display estimate. These placeholders are not a calibrated covariance model.
        for i in range(6):
            odometry.pose.covariance[i*7] = 100.0
            odometry.twist.covariance[i*7] = 100.0
        self.odometry.publish(odometry)
        if now-self.last_path_at > 0.2:
            if motion.speed or not self.path.poses:
                self.path.poses.append(PoseStamped(header=transform.header, pose=odometry.pose.pose))
                self.path.poses = self.path.poses[-1200:]
            self.path.header.stamp = stamp
            self.path_publisher.publish(self.path)
            self.last_path_at = now

        label = Marker()
        label.header.frame_id, label.header.stamp = 'base_link', stamp
        label.ns, label.id, label.type = 'command_telemetry', 0, Marker.TEXT_VIEW_FACING
        label.pose.orientation.w = 1.0
        label.pose.position.z, label.scale.z = 0.46, 0.016
        label.lifetime.sec = 1
        label.color.r, label.color.g, label.color.b, label.color.a = 0.08, 0.13, 0.18, 1.0
        source = 'DEMO' if self.demo else 'COMMAND_ESTIMATE\nNOT_MEASURED'
        sensor_text = []
        for topic, values in self.sensor_values.items():
            age = now-self.sensor_times.get(topic, -1e9)
            readings = '/'.join(map(str,values)) if values is not None and age < 1 else 'stale'
            sensor_text.append(f"{'US_cm' if topic == TOPICS[0] else 'IR_raw'}:{readings}")
        # Avoid Jazzy's disproportionate word spacing in small TEXT_VIEW_FACING markers.
        label.text = (f'{source}\nv={motion.speed:+.2f}m/s|steer={math.degrees(motion.steering):+.1f}deg'
                      f"\ncmd={'fresh' if fresh else 'stale/absent'}\n"+'\n'.join(sensor_text))
        self.telemetry.publish(MarkerArray(markers=[label]))

    def reset_estimate(self, request, response):
        self.motion.reset()
        self.path.poses.clear()
        return response

    def close(self):
        self.stopping.set()
        for worker in self.workers:
            worker.join()


def main():
    rclpy.init()
    node = TelemetryBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
