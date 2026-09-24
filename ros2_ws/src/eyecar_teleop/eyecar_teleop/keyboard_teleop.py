"""Publish keyboard commands as geometry_msgs/Twist."""

import codecs
import os
import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


HELP = """
EyeCar keyboard teleop
----------------------
W: forward     S: reverse
A: turn left   D: turn right
Space: stop    Q: quit

Movement keys can be combined: W+A, W+D, S+A, S+D.

English and Russian keyboard layouts are supported.

Hold/repeat a movement key to keep moving. If input stops, the node publishes
zero velocity automatically.
"""


class KeyboardTeleop(Node):
    """Read single terminal keys and publish velocity commands."""

    def __init__(self) -> None:
        super().__init__('keyboard_teleop')

        self.declare_parameter('topic', '/cmd_vel')
        self.declare_parameter('forward_speed', 0.18)
        self.declare_parameter('reverse_speed', 0.25)
        self.declare_parameter('angular_speed', 0.85)
        self.declare_parameter('command_timeout', 0.35)
        self.declare_parameter('publish_rate', 10.0)

        self.topic = str(self.get_parameter('topic').value)
        self.forward_speed = float(self.get_parameter('forward_speed').value)
        self.reverse_speed = float(self.get_parameter('reverse_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)
        self.command_timeout = float(self.get_parameter('command_timeout').value)
        publish_rate = float(self.get_parameter('publish_rate').value)

        if publish_rate <= 0.0:
            raise ValueError('publish_rate must be greater than zero')
        if self.command_timeout <= 0.0:
            raise ValueError('command_timeout must be greater than zero')
        if self.forward_speed <= 0.0 or self.reverse_speed <= 0.0:
            raise ValueError('forward_speed and reverse_speed must be positive')

        self.publisher = self.create_publisher(Twist, self.topic, 10)
        self.linear = 0.0
        self.angular = 0.0
        self.last_command_at = 0.0
        self.quit_requested = False
        self.key_decoder = codecs.getincrementaldecoder('utf-8')()
        self.timer = self.create_timer(1.0 / publish_rate, self.on_timer)

        self.get_logger().info(
            f'Publishing keyboard commands to {self.topic}; '
            f'timeout={self.command_timeout:.2f}s'
        )
        print(HELP, flush=True)

    def read_keys(self) -> list[str]:
        """Read every byte currently available without TextIO buffering."""
        chunks: list[bytes] = []
        while select.select([sys.stdin], [], [], 0.0)[0]:
            chunk = os.read(sys.stdin.fileno(), 64)
            if not chunk:
                break
            chunks.append(chunk)
        if not chunks:
            return []
        return list(self.key_decoder.decode(b''.join(chunks)).lower())

    def apply_key(self, key: str) -> None:
        """Convert a key into a velocity command."""
        key = {
            'ц': 'w',
            'ы': 's',
            'ф': 'a',
            'в': 'd',
            'й': 'q',
        }.get(key, key)

        if key == 'q':
            self.linear = 0.0
            self.angular = 0.0
            self.publish_command()
            self.get_logger().info('Q: stop and quit')
            self.quit_requested = True
            return

        previous = (self.linear, self.angular)
        if key == 'w':
            self.linear = self.forward_speed
        elif key == 's':
            self.linear = -self.reverse_speed
        elif key == 'a':
            self.angular = self.angular_speed
        elif key == 'd':
            self.angular = -self.angular_speed
        elif key == ' ':
            self.linear = 0.0
            self.angular = 0.0
        else:
            if key not in ('\r', '\n'):
                self.get_logger().warning(f'Ignored key: {key!r}')
            return

        changed = previous != (self.linear, self.angular)
        self.last_command_at = time.monotonic()
        if changed or key == ' ':
            label = 'Space' if key == ' ' else key.upper()
            self.get_logger().info(
                f'{label}: linear.x={self.linear:+.3f}, '
                f'angular.z={self.angular:+.3f}'
            )

    def publish_command(self) -> None:
        """Publish the current command."""
        message = Twist()
        message.linear.x = self.linear
        message.angular.z = self.angular
        self.publisher.publish(message)

    def on_timer(self) -> None:
        """Read input, apply the watchdog and publish at a fixed rate."""
        for key in self.read_keys():
            self.apply_key(key)

        command_age = time.monotonic() - self.last_command_at
        moving = self.linear != 0.0 or self.angular != 0.0
        if moving and command_age > self.command_timeout:
            self.linear = 0.0
            self.angular = 0.0

        self.publish_command()


def main(args=None) -> None:
    """Run keyboard teleoperation in a real terminal."""
    if not sys.stdin.isatty():
        raise RuntimeError('keyboard_teleop must run in an interactive terminal')

    terminal_settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=args)
    node = KeyboardTeleop()

    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok() and not node.quit_requested:
            rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.linear = 0.0
        node.angular = 0.0
        node.publish_command()
        rclpy.spin_once(node, timeout_sec=0.05)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, terminal_settings)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
