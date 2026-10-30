import os
from pathlib import Path
import sys
import time

assert os.environ.get('EYECAR_RVIZ_DIRECT') == '1'
assert os.environ.get('EYECAR_RVIZ_DEMO') != '1'
assert os.environ.get('ROS_DOMAIN_ID') not in (None, '0', '81')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import UInt16MultiArray
from rviz_bridge import TelemetryBridge, TOPICS

rclpy.init()
bridge = TelemetryBridge()
producer = Node('test_rover')
executor = SingleThreadedExecutor()
executor.add_node(bridge)
executor.add_node(producer)
publishers = [producer.create_publisher(kind, topic, 10) for topic, kind in
              zip(TOPICS, (UInt16MultiArray, UInt16MultiArray, Twist))]
messages = [UInt16MultiArray(data=[10, 20, 30, 40]),
            UInt16MultiArray(data=[100, 200, 300, 400, 500]), Twist()]

try:
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        for publisher, message in zip(publishers, messages):
            publisher.publish(message)
        executor.spin_once(timeout_sec=0.02)
    assert bridge.sensor_values[TOPICS[0]] == [10, 20, 30, 40]
    assert bridge.sensor_values[TOPICS[1]] == [100, 200, 300, 400, 500]
    assert not bridge.workers and not bridge.publishers_by_topic
    for topic in TOPICS:
        names = [p.node_name for p in bridge.get_publishers_info_by_topic(topic)]
        assert names == ['test_rover'], (topic, names)
    bridge.receive_ros(TOPICS[0], UInt16MultiArray(data=[500, 20, 30, 40]))
    bridge.publish_latest()
    assert bridge.sensor_values[TOPICS[0]] == [10, 20, 30, 40]
    print('PASS: direct ROS telemetry, offline DDS profile, no raw-topic republishing, invalid data ignored')
finally:
    bridge.close()
    executor.shutdown()
    bridge.destroy_node()
    producer.destroy_node()
    rclpy.try_shutdown()
