#!/usr/bin/env python3
"""Set all 13 EyeCar pixels through the ROS 2 per-pixel service."""

import argparse
import os

# Use the same local-only DDS profile as the EyeCar services.
os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'
os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
os.environ['CYCLONEDDS_URI'] = 'file:///home/mavxa/eyecar_web/cyclonedds-loopback.xml'

import rclpy
from rclpy.node import Node

from eyecar_interfaces.msg import LedState
from eyecar_interfaces.srv import SetLeds


LED_COUNT = 13
RGB = ((255, 0, 0), (0, 255, 0), (0, 0, 255))


def color_for(mode: str, index: int) -> tuple[int, int, int]:
    if mode == 'white':
        return 255, 255, 255
    if mode == 'off':
        return 0, 0, 0
    if mode == 'rgb':
        return RGB[index % len(RGB)]
    return (255, 0, 0) if index < (LED_COUNT + 1) // 2 else (0, 0, 255)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('white', 'rgb', 'off', 'halves'))
    mode = parser.parse_args().mode

    rclpy.init()
    node = Node('eyecar_led_modes_example')
    try:
        client = node.create_client(SetLeds, '/eyecar/led/set_leds')
        if not client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('LED service is unavailable')

        request = SetLeds.Request()
        for index in range(LED_COUNT):
            red, green, blue = color_for(mode, index)
            request.leds.append(
                LedState(index=index, r=red, g=green, b=blue)
            )
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10.0)
        if not future.done() or future.result() is None:
            raise RuntimeError('LED service did not respond')
        if not future.result().success:
            raise RuntimeError(future.result().message)
        print(f'{mode}: {future.result().message}')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
