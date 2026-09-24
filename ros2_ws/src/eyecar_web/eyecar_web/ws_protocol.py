"""Small RFC 6455 implementation used by the local EyeCar panel."""

from __future__ import annotations

import base64
import hashlib
import json
import struct
from typing import BinaryIO


WEBSOCKET_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA
MAX_FRAME_BYTES = 1 << 20


def parse_handshake(request: bytes) -> str | None:
    try:
        text = request.decode('latin-1')
    except UnicodeDecodeError:
        return None
    lines = text.split('\r\n')
    if not lines or not lines[0].upper().startswith('GET '):
        return None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, separator, value = line.partition(':')
        if separator:
            headers[name.strip().lower()] = value.strip()
    if 'websocket' not in headers.get('upgrade', '').lower():
        return None
    return headers.get('sec-websocket-key') or None


def handshake_response(key: str) -> bytes:
    digest = hashlib.sha1((key + WEBSOCKET_GUID).encode('ascii')).digest()
    accept = base64.b64encode(digest).decode('ascii')
    return (
        'HTTP/1.1 101 Switching Protocols\r\n'
        'Upgrade: websocket\r\n'
        'Connection: Upgrade\r\n'
        f'Sec-WebSocket-Accept: {accept}\r\n'
        '\r\n'
    ).encode('ascii')


def encode_frame(payload: bytes, opcode: int = OPCODE_TEXT) -> bytes:
    header = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header += struct.pack('!H', length)
    else:
        header.append(127)
        header += struct.pack('!Q', length)
    return bytes(header) + payload


def encode_json(payload: dict) -> bytes:
    return encode_frame(
        json.dumps(payload, separators=(',', ':')).encode('utf-8')
    )


def read_exactly(stream: BinaryIO, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise ConnectionError('websocket closed mid-frame')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def read_frame(stream: BinaryIO) -> tuple[int, bool, bytes]:
    first, second = read_exactly(stream, 2)
    final = bool(first & 0x80)
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        (length,) = struct.unpack('!H', read_exactly(stream, 2))
    elif length == 127:
        (length,) = struct.unpack('!Q', read_exactly(stream, 8))
    if length > MAX_FRAME_BYTES:
        raise ConnectionError(f'oversized websocket frame: {length}')
    mask = read_exactly(stream, 4) if masked else b''
    payload = read_exactly(stream, length) if length else b''
    if masked:
        payload = bytes(
            value ^ mask[index % 4]
            for index, value in enumerate(payload)
        )
    return opcode, final, payload


def read_message(stream: BinaryIO) -> tuple[int, bytes]:
    opcode, final, payload = read_frame(stream)
    if opcode in (OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG):
        return opcode, payload
    chunks = [payload]
    while not final:
        next_opcode, final, payload = read_frame(stream)
        if next_opcode == OPCODE_CLOSE:
            raise ConnectionError('websocket closed mid-message')
        if next_opcode not in (OPCODE_PING, OPCODE_PONG):
            chunks.append(payload)
    return opcode, b''.join(chunks)
