"""Bridge geometry_msgs/Twist commands to the EyeCar serial controller."""

from __future__ import annotations

import time

import rclpy
import serial
from geometry_msgs.msg import Twist
from rclpy.node import Node


PROTOCOL_BANNER = 'READY EYECAR_BASE_V1'


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class EyeCarSerialDriver(Node):
    """Send bounded commands only to firmware that confirms our protocol."""

    def __init__(self) -> None:
        super().__init__('eyecar_serial_driver')

        self.declare_parameter(
            'port',
            '/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0',
        )
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('command_rate', 20.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('handshake_timeout', 5.0)
        self.declare_parameter('reconnect_interval', 2.0)
        self.declare_parameter('max_linear_speed', 0.25)
        self.declare_parameter('max_angular_speed', 0.85)
        self.declare_parameter('motion_enabled', True)

        self.port = str(self.get_parameter('port').value)
        self.baud_rate = int(self.get_parameter('baud_rate').value)
        command_rate = float(self.get_parameter('command_rate').value)
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.handshake_timeout = float(
            self.get_parameter('handshake_timeout').value
        )
        self.reconnect_interval = float(
            self.get_parameter('reconnect_interval').value
        )
        self.max_linear_speed = float(
            self.get_parameter('max_linear_speed').value
        )
        self.max_angular_speed = float(
            self.get_parameter('max_angular_speed').value
        )
        self.motion_enabled = bool(
            self.get_parameter('motion_enabled').value
        )

        if command_rate <= 0.0:
            raise ValueError('command_rate must be greater than zero')
        if self.cmd_timeout <= 0.0:
            raise ValueError('cmd_timeout must be greater than zero')
        if self.max_linear_speed <= 0.0:
            raise ValueError('max_linear_speed must be greater than zero')
        if self.max_angular_speed <= 0.0:
            raise ValueError('max_angular_speed must be greater than zero')

        self.serial_port: serial.Serial | None = None
        self.connected_at = 0.0
        self.last_connect_attempt = 0.0
        self.handshake_complete = False
        self.handshake_warning_emitted = False
        self.receive_buffer = bytearray()
        self.sequence = 0
        self.last_reported_command: tuple[int, int] | None = None

        self.linear = 0.0
        self.angular = 0.0
        self.last_command_at = 0.0

        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.on_command,
            10,
        )
        self.timer = self.create_timer(1.0 / command_rate, self.on_timer)

        if self.motion_enabled:
            self.get_logger().warning(
                'Physical motion is ENABLED; keep wheels clear'
            )
        else:
            self.get_logger().warning(
                'Physical motion is disabled; only zero commands will be sent'
            )

    def on_command(self, message: Twist) -> None:
        self.linear = float(message.linear.x)
        self.angular = float(message.angular.z)
        self.last_command_at = time.monotonic()

    def connect(self) -> None:
        now = time.monotonic()
        if now - self.last_connect_attempt < self.reconnect_interval:
            return
        self.last_connect_attempt = now

        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=0,
                write_timeout=0.2,
            )
        except (OSError, serial.SerialException) as error:
            self.get_logger().error(f'Cannot open {self.port}: {error}')
            self.serial_port = None
            return

        self.connected_at = now
        self.handshake_complete = False
        self.handshake_warning_emitted = False
        self.receive_buffer.clear()
        self.get_logger().info(
            f'Opened {self.port} at {self.baud_rate} baud; waiting for firmware'
        )

    def disconnect(self, error: Exception) -> None:
        self.get_logger().error(f'Serial connection failed: {error}')
        if self.serial_port is not None:
            try:
                self.serial_port.close()
            except (OSError, serial.SerialException):
                pass
        self.serial_port = None
        self.handshake_complete = False

    def poll_input(self) -> None:
        if self.serial_port is None:
            return

        waiting = self.serial_port.in_waiting
        if waiting:
            self.receive_buffer.extend(self.serial_port.read(waiting))

        while b'\n' in self.receive_buffer:
            raw_line, _, remainder = self.receive_buffer.partition(b'\n')
            self.receive_buffer = bytearray(remainder)
            line = raw_line.decode('utf-8', errors='replace').strip()
            if not line:
                continue
            if line == PROTOCOL_BANNER:
                self.handshake_complete = True
                self.get_logger().info('EyeCar controller handshake complete')
            elif line.startswith(('ERR', 'WATCHDOG')):
                self.get_logger().warning(f'Controller: {line}')
            else:
                self.get_logger().debug(f'Controller: {line}')

    def normalized_command(self) -> tuple[int, int]:
        command_fresh = (
            self.last_command_at > 0.0
            and time.monotonic() - self.last_command_at <= self.cmd_timeout
        )
        if not self.motion_enabled or not command_fresh:
            return 0, 0

        throttle = clamp(
            self.linear / self.max_linear_speed,
            -1.0,
            1.0,
        )
        steering = clamp(
            self.angular / self.max_angular_speed,
            -1.0,
            1.0,
        )
        return round(throttle * 1000), round(steering * 1000)

    def send_command(self) -> None:
        if self.serial_port is None or not self.handshake_complete:
            return

        throttle, steering = self.normalized_command()
        command = (throttle, steering)
        if command != self.last_reported_command:
            self.get_logger().info(
                f'Serial command: throttle={throttle:+d}, '
                f'steering={steering:+d}'
            )
            self.last_reported_command = command
        self.sequence = (self.sequence + 1) & 0xFFFFFFFF
        packet = f'C {self.sequence} {throttle} {steering}\n'.encode('ascii')
        self.serial_port.write(packet)

    def on_timer(self) -> None:
        if self.serial_port is None:
            self.connect()
            return

        try:
            self.poll_input()
            if (
                not self.handshake_complete
                and not self.handshake_warning_emitted
                and time.monotonic() - self.connected_at > self.handshake_timeout
            ):
                self.handshake_warning_emitted = True
                self.get_logger().error(
                    f'No {PROTOCOL_BANNER!r} banner; refusing to send commands'
                )
            self.send_command()
        except (OSError, serial.SerialException) as error:
            self.disconnect(error)

    def stop_and_close(self) -> None:
        if self.serial_port is None:
            return
        try:
            if self.handshake_complete:
                self.serial_port.write(b'STOP\n')
                self.serial_port.flush()
        except (OSError, serial.SerialException):
            pass
        finally:
            self.serial_port.close()
            self.serial_port = None


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EyeCarSerialDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_and_close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
