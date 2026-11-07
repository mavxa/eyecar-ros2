"""Run only against the isolated, running EyeCar Webots scene (domain 42)."""
import os
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, JointState
from std_msgs.msg import ColorRGBA, UInt8, UInt16MultiArray
from eyecar_interfaces.msg import LedState, LedStateArray
from eyecar_interfaces.srv import SetLeds

assert os.environ.get('ROS_DOMAIN_ID') == '42', 'Use the isolated simulation domain'
rclpy.init()
node = rclpy.create_node('webots_integration_check')
latest = {}
subscriptions = []
latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
for topic, kind, qos in [('/simulation/odom', Odometry, 10),
                         ('/joint_states', JointState, 10),
                         ('/camera/image_raw/compressed', CompressedImage, qos_profile_sensor_data),
                         ('/eyecar/ultrasonic', UInt16MultiArray, 10),
                         ('/eyecar/infrared', UInt16MultiArray, 10),
                         ('/eyecar/led/state', LedStateArray, latched),
                         ('/eyecar/led/brightness_state', UInt8, latched)]:
    subscriptions.append(node.create_subscription(kind, topic,
                         lambda msg, topic=topic: latest.update({topic: msg}), qos))


def until(predicate, timeout=12):
    end = time.monotonic()+timeout
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.02)
        if predicate():
            return
    raise AssertionError(f'Timed out; received {list(latest)}')


def simulated_time():
    stamp = latest['/simulation/odom'].header.stamp
    return stamp.sec+stamp.nanosec/1e9


def drive(linear, angular, duration):
    begin = simulated_time()
    command = Twist()
    command.linear.x, command.angular.z = float(linear), float(angular)
    end = time.monotonic()+20
    while simulated_time()-begin < duration:
        assert time.monotonic() < end, 'Simulation stopped advancing'
        velocity.publish(command)
        rclpy.spin_once(node, timeout_sec=0.02)


velocity = node.create_publisher(Twist, '/cmd_vel', 10)
try:
    until(lambda: len(latest) == 7)
    publishers = node.get_publishers_info_by_topic('/simulation/odom')
    assert publishers and all(p.node_name == 'eyecar_sim_driver' for p in publishers)
    # Only the simulation marker above authorizes sending test commands.
    assert len(latest['/eyecar/ultrasonic'].data) == 4
    assert len(latest['/eyecar/infrared'].data) == 5
    jpeg = latest['/camera/image_raw/compressed']
    image = cv2.imdecode(np.frombuffer(jpeg.data, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape == (240, 320, 3)
    assert np.std(image) > 5, 'Camera returned a blank image'
    assert np.count_nonzero((image[:, :, 0] > 120) & (image[:, :, 2] < 100)) > 50, 'Blue target is outside the camera view'
    b, g, r = image.astype(np.float32).transpose(2, 0, 1)
    assert np.count_nonzero((g > r*1.2) & (g > b*1.2) & (g > 40)) > 30, 'Green ball is outside the camera view'
    Path('/tmp/eyecar-sim-camera.jpg').write_bytes(jpeg.data)
    print('PASS: camera JPEG, four sonar channels and five IR channels', flush=True)

    drive(0, 0, 0.3)
    initial = latest['/simulation/odom'].pose.pose.position.x
    drive(0.18, 0, 1.2)
    forward = latest['/simulation/odom'].pose.pose.position.x
    assert forward-initial > 0.10, (initial, forward)
    drive(-0.18, 0, 1.2)
    backward = latest['/simulation/odom'].pose.pose.position.x
    assert forward-backward > 0.10, (forward, backward)
    drive(0.18, 0, 6)
    at_wall = latest['/simulation/odom'].pose.pose.position.x
    assert 0.65 < at_wall < 0.86, f'Robot did not stop at the wall: x={at_wall}'
    assert 0 < latest['/eyecar/ultrasonic'].data[3] < 20
    drive(-0.18, 0, 4)
    print('PASS: bumper collision and front-sonar centimetres', flush=True)
    drive(0.18, 0.85, 1.2)
    joints = latest['/joint_states']
    positions = dict(zip(joints.name, joints.position))
    assert positions['front_left_steering'] > positions['front_right_steering'] > 0.1
    assert abs(latest['/simulation/odom'].pose.pose.orientation.z) > 0.08
    drive(0, 0, 0.4)
    start = simulated_time()
    once = Twist(); once.linear.x = 0.18
    velocity.publish(once)
    until(lambda: simulated_time()-start > 1.2)
    assert abs(latest['/simulation/odom'].twist.twist.linear.x) < 0.025
    print('PASS: physical forward/reverse, Ackermann turn and stale-command stop', flush=True)

    color = node.create_publisher(ColorRGBA, '/eyecar/led/color', 10)
    until(lambda: color.get_subscription_count() > 0)
    color.publish(ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0))
    until(lambda: len(latest['/eyecar/led/state'].leds) == 13 and
          all((p.r, p.g, p.b) == (0, 255, 0) for p in latest['/eyecar/led/state'].leds))
    client = node.create_client(SetLeds, '/eyecar/led/set_leds')
    assert client.wait_for_service(timeout_sec=3)
    request = SetLeds.Request(leds=[LedState(index=0, r=255, g=0, b=0)])
    future = client.call_async(request)
    until(future.done)
    assert future.result().success
    until(lambda: latest['/eyecar/led/state'].leds[0].r == 255)
    print('PASS: LED fill and individual-pixel service', flush=True)
finally:
    velocity.publish(Twist())
    node.destroy_node()
    rclpy.try_shutdown()
