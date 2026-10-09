"""Publish keyboard commands as geometry_msgs/Twist."""

import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

from eyecar_teleop.keyboard_protocol import KeyEvent, TerminalKeyboard


HELP = """
EyeCar keyboard teleop
----------------------
W / Up: forward       S / Down: reverse
A / Left: turn left   D / Right: turn right
Space: stop    Q: quit

Movement keys can be combined: W+A, W+D, S+A, S+D.

English and Russian keyboard layouts are supported.

Hold movement keys to keep moving. Compatible terminals report key releases,
so releasing a key stops that axis immediately. Other terminals use key repeat.
If input stops, the node publishes zero velocity automatically.

Steam Deck over SSH: map the D-pad/stick to WASD (or arrow keys),
one button to Space and another to Q. For reliable combined directions
in terminals without key releases, repeat each mapped movement key
every 50-100 ms in Steam Input. Throttle and steering expire separately.
"""


class KeyboardTeleop(Node):
    """Read single terminal keys and publish velocity commands."""

    def __init__(self, keyboard: TerminalKeyboard) -> None:
        super().__init__('keyboard_teleop')

        self.declare_parameter('topic', '/cmd_vel')
        self.declare_parameter('forward_speed', 0.18)
        self.declare_parameter('reverse_speed', 0.25)
        self.declare_parameter('angular_speed', 0.85)
        self.declare_parameter('command_timeout', 0.5)
        self.declare_parameter('publish_rate', 20.0)

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
        self.keyboard = keyboard
        self.held_keys: set[str] = set()
        self.linear = 0.0
        self.angular = 0.0
        self.last_command_at = 0.0
        self.last_linear_at = 0.0
        self.last_angular_at = 0.0
        self.quit_requested = False
        self.timer = self.create_timer(1.0 / publish_rate, self.on_timer)

        self.get_logger().info(
            f'Publishing keyboard commands to {self.topic}; '
            f'timeout={self.command_timeout:.2f}s; '
            f'key releases={keyboard.releases_available}'
        )
        print(HELP, flush=True)

    def apply_event(self, event: KeyEvent) -> None:
        """Convert a terminal key event into velocity and send changes now."""
        key = event.key
        key = {
            'ц': 'w',
            'ы': 's',
            'ф': 'a',
            'в': 'd',
            'й': 'q',
        }.get(key, key)

        if key == 'q' and event.kind == 'release':
            return
        if key == 'q':
            self.linear = 0.0
            self.angular = 0.0
            self.held_keys.clear()
            self.publish_command()
            self.get_logger().info('Q: stop and quit')
            self.quit_requested = True
            return

        if key == ' ':
            if event.kind == 'release':
                return
            previous = (self.linear, self.angular)
            self.held_keys.clear()
            self.linear = 0.0
            self.angular = 0.0
            self.last_command_at = time.monotonic()
            self.publish_command()
            if previous != (0.0, 0.0):
                self.get_logger().info('Space: stop')
            return

        if key not in ('w', 's', 'a', 'd'):
            if key not in ('\r', '\n'):
                self.get_logger().warning(f'Ignored key: {key!r}')
            return

        previous = (self.linear, self.angular)
        if self.keyboard.releases_available:
            if event.kind == 'release':
                self.held_keys.discard(key)
            else:
                self.held_keys.add(key)
            self.linear = (
                self.forward_speed
                if 'w' in self.held_keys and 's' not in self.held_keys
                else -self.reverse_speed
                if 's' in self.held_keys and 'w' not in self.held_keys
                else 0.0
            )
            self.angular = (
                self.angular_speed
                if 'a' in self.held_keys and 'd' not in self.held_keys
                else -self.angular_speed
                if 'd' in self.held_keys and 'a' not in self.held_keys
                else 0.0
            )
        elif event.kind != 'release':
            if key == 'w':
                self.linear = self.forward_speed
            elif key == 's':
                self.linear = -self.reverse_speed
            elif key == 'a':
                self.angular = self.angular_speed
            else:
                self.angular = -self.angular_speed

        changed = previous != (self.linear, self.angular)
        if event.kind != 'release':
            self.last_command_at = time.monotonic()
            if key in ('w', 's'):
                self.last_linear_at = self.last_command_at
            else:
                self.last_angular_at = self.last_command_at
        if changed:
            self.publish_command()
            label = key.upper() + (' released' if event.kind == 'release' else '')
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
        """Apply the input watchdog and refresh the controller command."""
        now = time.monotonic()
        command_age = now - self.last_command_at
        moving = self.linear != 0.0 or self.angular != 0.0
        if not self.keyboard.releases_available:
            # A repeating steering key must not keep an old throttle command alive.
            if now - self.last_linear_at > self.command_timeout:
                self.linear = 0.0
            if now - self.last_angular_at > self.command_timeout:
                self.angular = 0.0
        elif moving and command_age > self.command_timeout:
            self.linear = 0.0
            self.angular = 0.0
            self.held_keys.clear()

        self.publish_command()


def main(args=None) -> None:
    """Use terminal keys, or analog gamepad packets piped through SSH."""
    if not sys.stdin.isatty():
        from eyecar_teleop.steamdeck_teleop import main as gamepad_main
        gamepad_main(
            args=args, node_name='keyboard_teleop',
            topic_parameter='topic', default_topic='/cmd_vel')
        return

    terminal_settings = termios.tcgetattr(sys.stdin)
    keyboard = TerminalKeyboard()
    node = None
    try:
        tty.setcbreak(sys.stdin.fileno())
        keyboard.enable_release_events()
        rclpy.init(args=args)
        node = KeyboardTeleop(keyboard)
        while rclpy.ok() and not node.quit_requested:
            for event in keyboard.read_events():
                node.apply_event(event)
            rclpy.spin_once(node, timeout_sec=0.01)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.linear = 0.0
            node.angular = 0.0
            node.publish_command()
            rclpy.spin_once(node, timeout_sec=0.05)
            node.destroy_node()
        keyboard.disable_release_events()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, terminal_settings)
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
