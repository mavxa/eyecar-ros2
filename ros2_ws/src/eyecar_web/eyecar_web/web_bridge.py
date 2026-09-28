"""Read-only ROS topic browser for the EyeCar web panel."""

from __future__ import annotations

import base64
import contextlib
import json
import queue
import socket
import threading
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.utilities import get_message

from eyecar_web.ws_protocol import (
    OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG, OPCODE_TEXT,
    encode_frame, encode_json, handshake_response, parse_handshake, read_message,
)

HANDSHAKE_LIMIT = 8192
MAX_JSON_BYTES = 64 * 1024
MAX_IMAGE_BYTES = 1024 * 1024


class PanelClient:
    def __init__(self, connection: socket.socket) -> None:
        self.connection = connection
        self.outgoing: queue.Queue[bytes | None] = queue.Queue(maxsize=16)
        self.topic: str | None = None
        self.closed = False
        threading.Thread(target=self._send_loop, daemon=True).start()

    def send(self, payload: dict) -> None:
        self._queue(encode_json(payload))

    def send_frame(self, payload: bytes, opcode: int = OPCODE_TEXT) -> None:
        self._queue(encode_frame(payload, opcode))

    def _queue(self, frame: bytes) -> None:
        if self.closed:
            return
        try:
            self.outgoing.put_nowait(frame)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                self.outgoing.get_nowait()
            with contextlib.suppress(queue.Full):
                self.outgoing.put_nowait(frame)

    def _send_loop(self) -> None:
        try:
            while True:
                frame = self.outgoing.get()
                if frame is None:
                    return
                self.connection.sendall(frame)
        except OSError:
            self.close()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        with contextlib.suppress(OSError):
            self.connection.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(OSError):
            self.connection.close()
        with contextlib.suppress(queue.Full):
            self.outgoing.put_nowait(None)


def serialize_message(message: object, type_name: str) -> dict:
    if type_name == 'sensor_msgs/msg/Image':
        return {
            'width': message.width, 'height': message.height,
            'encoding': message.encoding, 'step': message.step,
            'bytes': len(message.data),
            'note': 'Raw pixels are omitted from the text viewer.',
        }
    if type_name == 'sensor_msgs/msg/CompressedImage':
        data = bytes(message.data)
        result = {'format': message.format, 'bytes': len(data)}
        if 'jpeg' in message.format.lower() and len(data) <= MAX_IMAGE_BYTES:
            result['jpeg_base64'] = base64.b64encode(data).decode('ascii')
        return result
    return message_to_ordereddict(message)


class EyeCarWebBridge(Node):
    def __init__(self) -> None:
        super().__init__('eyecar_web_bridge')
        self.declare_parameter('address', '127.0.0.1')
        self.declare_parameter('port', 9090)
        self.clients: set[PanelClient] = set()
        self.clients_lock = threading.Lock()
        self.topic_snapshot: dict[str, str] = {}
        self.subscriptions: dict[str, tuple[str, object]] = {}
        self.last_sent: dict[str, float] = {}
        self.stopping = threading.Event()
        self.create_timer(0.2, self._refresh_topics_and_watches)
        self._refresh_topics_and_watches()

        address = str(self.get_parameter('address').value)
        port = int(self.get_parameter('port').value)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((address, port))
        self.listener.listen(8)
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self.get_logger().info(f'Read-only topic bridge on {address}:{port}')

    def _refresh_topics_and_watches(self) -> None:
        snapshot = {
            name: types[0] for name, types in self.get_topic_names_and_types()
            if len(types) == 1
        }
        with self.clients_lock:
            self.topic_snapshot = snapshot
            wanted = {client.topic for client in self.clients if client.topic}

        for name, (type_name, subscription) in list(self.subscriptions.items()):
            if name not in wanted or snapshot.get(name) != type_name:
                self.destroy_subscription(subscription)
                del self.subscriptions[name]
                self.last_sent.pop(name, None)

        for name in wanted - self.subscriptions.keys():
            type_name = snapshot.get(name)
            if type_name is None:
                continue
            try:
                subscription = self.create_subscription(
                    get_message(type_name), name,
                    lambda msg, topic=name, kind=type_name: self._on_message(
                        topic, kind, msg),
                    QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT),
                )
                self.subscriptions[name] = (type_name, subscription)
            except (ImportError, ValueError, RuntimeError) as exc:
                self.get_logger().warning(f'Cannot watch {name}: {exc}')

    def _on_message(self, topic: str, type_name: str, message: object) -> None:
        now = time.monotonic()
        if now - self.last_sent.get(topic, 0.0) < 0.1:
            return
        self.last_sent[topic] = now
        try:
            result = {
                'op': 'message', 'topic': topic,
                'msg': serialize_message(message, type_name),
            }
            if (type_name != 'sensor_msgs/msg/CompressedImage'
                    and len(json.dumps(result).encode('utf-8')) > MAX_JSON_BYTES):
                result['msg'] = {'note': 'Message exceeds the 64 KiB viewer limit.'}
        except (TypeError, ValueError, AttributeError) as exc:
            self.get_logger().warning(f'Cannot display {topic}: {exc}')
            return
        with self.clients_lock:
            clients = tuple(c for c in self.clients if c.topic == topic)
        for client in clients:
            client.send(result)

    def _accept_loop(self) -> None:
        while not self.stopping.is_set():
            try:
                connection, address = self.listener.accept()
            except OSError:
                return
            threading.Thread(
                target=self._serve, args=(connection, address), daemon=True,
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
        client = None
        try:
            connection.settimeout(5.0)
            key = parse_handshake(self._read_handshake(connection))
            if key is None:
                return
            connection.sendall(handshake_response(key))
            connection.settimeout(None)
            client = PanelClient(connection)
            with self.clients_lock:
                self.clients.add(client)
            self.get_logger().info(f'Viewer connected: {address[0]}')
            stream = connection.makefile('rb')
            while not self.stopping.is_set() and not client.closed:
                opcode, payload = read_message(stream)
                if opcode == OPCODE_CLOSE:
                    return
                if opcode == OPCODE_PING:
                    client.send_frame(payload, OPCODE_PONG)
                elif opcode == OPCODE_TEXT:
                    self._handle(client, payload)
        except (ConnectionError, OSError, ValueError, json.JSONDecodeError):
            pass
        finally:
            if client is not None:
                with self.clients_lock:
                    self.clients.discard(client)
                client.close()
            else:
                with contextlib.suppress(OSError):
                    connection.close()

    def _handle(self, client: PanelClient, raw: bytes) -> None:
        request = json.loads(raw.decode('utf-8'))
        if not isinstance(request, dict):
            client.send({'op': 'error', 'message': 'Invalid request'})
            return
        operation = request.get('op')
        if operation == 'list_topics':
            with self.clients_lock:
                topics = dict(self.topic_snapshot)
            client.send({'op': 'topics', 'topics': topics})
        elif operation == 'watch':
            name = request.get('topic')
            if not isinstance(name, str):
                client.send({'op': 'error', 'message': 'Invalid topic'})
                return
            with self.clients_lock:
                type_name = self.topic_snapshot.get(name)
                if type_name:
                    client.topic = name
            if type_name:
                client.send({'op': 'watching', 'topic': name, 'type': type_name})
            else:
                client.send({'op': 'error', 'message': 'Unknown topic'})
        elif operation == 'unwatch':
            with self.clients_lock:
                client.topic = None
        else:
            client.send({'op': 'error', 'message': 'Read-only bridge'})

    def shutdown(self) -> None:
        self.stopping.set()
        with contextlib.suppress(OSError):
            self.listener.close()
        with self.clients_lock:
            clients = tuple(self.clients)
            self.clients.clear()
        for client in clients:
            client.close()


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
