"""Display EyeCar velocity commands without controlling hardware."""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class CmdVelMonitor(Node):
    """Subscribe to /cmd_vel and print the relevant fields."""

    def __init__(self) -> None:
        super().__init__('cmd_vel_monitor')
        self.declare_parameter('topic', '/cmd_vel')
        topic = str(self.get_parameter('topic').value)
        self.subscription = self.create_subscription(
            Twist,
            topic,
            self.on_command,
            10,
        )
        self.get_logger().info(f'Monitoring {topic}')

    def on_command(self, message: Twist) -> None:
        self.get_logger().info(
            f'linear.x={message.linear.x:+.3f}, '
            f'angular.z={message.angular.z:+.3f}'
        )


def main(args=None) -> None:
    """Run the command monitor node."""
    rclpy.init(args=args)
    node = CmdVelMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
