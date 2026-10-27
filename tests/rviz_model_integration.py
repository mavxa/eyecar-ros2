"""Run inside the RViz image, in an isolated ROS domain with EYECAR_RVIZ_DEMO=1."""

import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.time import Time
from nav_msgs.msg import Odometry, Path as RosPath
from sensor_msgs.msg import JointState
from std_msgs.msg import String, UInt16MultiArray
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener
from rviz_bridge import TelemetryBridge

assert os.environ.get('EYECAR_RVIZ_DEMO') == '1', 'Use isolated demo mode, not the real rover'
assert os.environ.get('ROS_DOMAIN_ID') != '81', 'Use a separate test domain'
rclpy.init()
bridge = TelemetryBridge()
monitor = Node('eyecar_model_integration')
executor = SingleThreadedExecutor()
executor.add_node(bridge)
executor.add_node(monitor)
seen = {}
for topic, kind in [('/eyecar/command_estimate',Odometry),('/eyecar/command_path',RosPath),
                    ('/joint_states',JointState),('/eyecar/ultrasonic',UInt16MultiArray)]:
    monitor.create_subscription(kind,topic,lambda message,topic=topic: seen.update({topic:message}),10)
monitor.create_subscription(String,'/robot_description',lambda message: seen.update({'description':message.data}),
                            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
buffer = Buffer()
listener = TransformListener(buffer,monitor)
model = subprocess.Popen(['ros2','run','robot_state_publisher','robot_state_publisher',
                          '--ros-args','--params-file','/tmp/eyecar-model/robot_state_publisher.yaml'])

def spin_for(seconds):
    deadline = time.monotonic()+seconds
    while time.monotonic()<deadline:
        executor.spin_once(timeout_sec=0.05)

try:
    spin_for(8)
    assert 'eyecar_visual' in seen['description']
    assert seen['/eyecar/command_estimate'].pose.pose.position.x>0.2
    assert len(seen['/eyecar/command_path'].poses)>5
    assert len(seen['/joint_states'].name)==6
    assert len(seen['/eyecar/ultrasonic'].data)==4
    assert bridge.motion.yaw>0
    for frame in ('camera_optical_frame','us_rear','front_left_wheel'):
        buffer.lookup_transform('command_odom',frame,Time())
    bridge.demo = False
    spin_for(1)
    x,y = bridge.motion.x,bridge.motion.y
    spin_for(0.3)
    assert bridge.motion.speed==0 and (x,y)==(bridge.motion.x,bridge.motion.y)
    client = monitor.create_client(Empty,'/eyecar/reset_command_estimate')
    assert client.wait_for_service(timeout_sec=2)
    future = client.call_async(Empty.Request())
    executor.spin_until_future_complete(future,timeout_sec=2)
    assert future.done() and future.exception() is None
    assert bridge.motion.x==0 and bridge.motion.y==0
    print('PASS: URDF description, TF camera/sensors/wheels, wheel joints, command estimate/path, timeout and reset service')
finally:
    bridge.close()
    bridge.destroy_node()
    monitor.destroy_node()
    rclpy.try_shutdown()
    model.terminate()
    try:
        model.wait(timeout=5)
    except subprocess.TimeoutExpired:
        model.kill()
        model.wait()
