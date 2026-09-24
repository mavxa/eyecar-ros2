"""Serve the rosbridge subset required by the EyeCar web panel."""

from __future__ import annotations

import contextlib
import json
import math
import queue
import socket
import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from eyecar_web.ws_protocol import (
    OPCODE_CLOSE,
    OPCODE_PING,
    OPCODE_TEXT,
    OPCODE_PONG,
    encode_frame,
    encode_json,
    handshake_response,
    parse_handshake,
    read_message,
)


HANDSHAKE_LIMIT = 8192


class EyeCarWebBridge(Node):
    def __init__(self) -> None:
        super().__init__('eyecar_web_bridge')
        self.declare_parameter('address', '0.0.0.0')
        self.declare_parameter('port', 9090)
        self.declare_parameter('max_forward', 0.18)
        self.declare_parameter('max_reverse', 0.25)
        self.declare_parameter('max_steering', 0.85)

        self.max_forward = float(self.get_parameter('max_forward').value)
        self.max_reverse = float(self.get_parameter('max_reverse').value)
        self.max_steering = float(self.get_parameter('max_steering').value)

        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.commands: queue.Queue[tuple[float, float]] = queue.Queue(maxsize=1)
        self.topic_snapshot: list[tuple[str, str]] = []
        self.snapshot_lock = threading.Lock()
        self.stopping = threading.Event()

        self.create_timer(0.02, self._publish_pending)
        self.create_timer(1.0, self._refresh_topics)
        self._refresh_topics()

        address = str(self.get_parameter('address').value)
        port = int(self.get_parameter('port').value)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((address, port))
        self.listener.listen(8)
        self.acceptor = threading.Thread(
            target=self._accept_loop,
            name='eyecar-web-accept',
            daemon=True,
        )
        self.acceptor.start()
        self.get_logger().info(f'WebSocket bridge listening on {address}:{port}')

    def _refresh_topics(self) -> None:
        snapshot = [
            (name, ', '.join(types))
            for name, types in self.get_topic_names_and_types()
        ]
        with self.snapshot_lock:
            self.topic_snapshot = snapshot

    def _queue_command(self, linear: float, angular: float) -> None:
        command = (linear, angular)
        with contextlib.suppress(queue.Empty):
            self.commands.get_nowait()
        with contextlib.suppress(queue.Full):
            self.commands.put_nowait(command)

    def _publish_pending(self) -> None:
        try:
            linear, angular = self.commands.get_nowait()
        except queue.Empty:
            return
        message = Twist()
        message.linear.x = linear
        message.angular.z = angular
        self.publisher.publish(message)

    def _accept_loop(self) -> None:
        while not self.stopping.is_set():
            try:
                connection, address = self.listener.accept()
            except OSError:
                return
            threading.Thread(
                target=self._serve,
                args=(connection, address),
                name='eyecar-web-client',
                daemon=True,
            ).start()

    @staticmethod
    def _read_handshake(connection: socket.socket) -> bytes:
        request = b''
        while b'\r\n\r\n' not in request:
            if len(request) > HANDSHAKE_LIMIT:
                raise ConnectionError('handshake too large')
            chunk = connection.recv(HANDSHAKE_LIMIT)
            if not chunk:
                raise ConnectionError('closed during handshake')
            request += chunk
        return request

    def _serve(self, connection: socket.socket, address: tuple) -> None:
        registered = False
        try:
            connection.settimeout(5.0)
            key = parse_handshake(self._read_handshake(connection))
            if key is None:
                return
            connection.sendall(handshake_response(key))
            connection.settimeout(None)
            registered = True
            self.get_logger().info(f'Panel connected: {address[0]}')
            stream = connection.makefile('rb')
            while not self.stopping.is_set():
                opcode, payload = read_message(stream)
                if opcode == OPCODE_CLOSE:
                    return
                if opcode == OPCODE_PING:
                    connection.sendall(encode_frame(payload, OPCODE_PONG))
                    continue
                if opcode == OPCODE_TEXT:
                    self._handle(connection, payload)
        except (ConnectionError, OSError, ValueError, json.JSONDecodeError):
            pass
        finally:
            self._queue_command(0.0, 0.0)
            with contextlib.suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError):
                connection.close()
            if registered:
                self.get_logger().info(f'Panel disconnected: {address[0]}')

    def _handle(self, connection: socket.socket, raw: bytes) -> None:
        request = json.loads(raw.decode('utf-8'))
        operation = request.get('op')
        if operation in ('advertise', 'unadvertise'):
            return
        if operation == 'publish' and request.get('topic') == '/cmd_vel':
            self._handle_command(request.get('msg', {}))
            return
        if (
            operation == 'call_service'
            and request.get('service') == '/rosapi/topics'
        ):
            with self.snapshot_lock:
                snapshot = list(self.topic_snapshot)
            connection.sendall(encode_json({
                'op': 'service_response',
                'id': request.get('id', ''),
                'service': '/rosapi/topics',
                'values': {
                    'topics': [name for name, _ in snapshot],
                    'types': [type_name for _, type_name in snapshot],
                },
                'result': True,
            }))

    def _handle_command(self, message: dict) -> None:
        linear = float(message.get('linear', {}).get('x', 0.0))
        angular = float(message.get('angular', {}).get('z', 0.0))
        if not math.isfinite(linear) or not math.isfinite(angular):
            return
        linear = max(-self.max_reverse, min(self.max_forward, linear))
        angular = max(-self.max_steering, min(self.max_steering, angular))
        self._queue_command(linear, angular)

    def shutdown(self) -> None:
        self._queue_command(0.0, 0.0)
        self._publish_pending()
        self.stopping.set()
        with contextlib.suppress(OSError):
            self.listener.close()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EyeCarWebBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
