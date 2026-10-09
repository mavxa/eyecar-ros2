"""Terminal key events, including releases when Kitty keyboard mode is available."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
import os
import re
import select
import sys
import time


KITTY_REPLY = re.compile(rb'\x1b\[\?\d+u')
KITTY_ENABLE = b'\x1b[>15u'  # disambiguate, event types, alternate keys, all keys
KITTY_DISABLE = b'\x1b[<u'
ARROW_KEYS = {ord('A'): 'w', ord('B'): 's', ord('C'): 'd', ord('D'): 'a'}


@dataclass(frozen=True)
class KeyEvent:
    key: str
    kind: str = 'press'


def parse_kitty_key(sequence: bytes) -> KeyEvent | None:
    """Decode a CSI-u press, repeat, or release using the physical key if known."""
    if not sequence.startswith(b'\x1b[') or not sequence.endswith(b'u'):
        return None
    try:
        parts = sequence[2:-1].decode('ascii').split(';')
        key_fields = parts[0].split(':')
        code = int(key_fields[2] or key_fields[0]) if len(key_fields) > 2 else int(key_fields[0])
        event_fields = parts[1].split(':') if len(parts) > 1 else []
        event_type = int(event_fields[1]) if len(event_fields) > 1 else 1
        if event_type not in (1, 2, 3):
            return None
        return KeyEvent(chr(code).lower(), ('press', 'repeat', 'release')[event_type - 1])
    except (ValueError, OverflowError):
        return None


class TerminalKeyboard:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.decoder = codecs.getincrementaldecoder('utf-8')()
        self.pending: list[KeyEvent] = []
        self.releases_available = False

    def enable_release_events(self) -> None:
        """Probe the terminal; unsupported terminals stay in legacy mode."""
        if not sys.stdout.isatty():
            return
        os.write(sys.stdout.fileno(), b'\x1b[?u')
        received = bytearray()
        deadline = time.monotonic() + 0.25
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if not select.select([sys.stdin], [], [], remaining)[0]:
                break
            chunk = os.read(sys.stdin.fileno(), 128)
            if not chunk:
                break
            received.extend(chunk)
            match = KITTY_REPLY.search(received)
            if match:
                self.releases_available = True
                os.write(sys.stdout.fileno(), KITTY_ENABLE)
                del received[match.start():match.end()]
                break
        self.pending.extend(self.feed(bytes(received)))

    def disable_release_events(self) -> None:
        if self.releases_available:
            os.write(sys.stdout.fileno(), KITTY_DISABLE)

    def feed(self, data: bytes) -> list[KeyEvent]:
        self.buffer.extend(data)
        events: list[KeyEvent] = []
        while self.buffer:
            if self.buffer[0] != 0x1b:
                escape_at = self.buffer.find(0x1b)
                length = escape_at if escape_at >= 0 else len(self.buffer)
                plain = bytes(self.buffer[:length])
                del self.buffer[:length]
                events.extend(KeyEvent(char.lower()) for char in self.decoder.decode(plain))
                continue
            if len(self.buffer) < 2:
                break
            if self.buffer[1] == ord('O'):
                if len(self.buffer) < 3:
                    break
                key = ARROW_KEYS.get(self.buffer[2])
                del self.buffer[:3]
                if key is not None:
                    events.append(KeyEvent(key))
                continue
            if self.buffer[1] != ord('['):
                del self.buffer[0]
                continue
            end = next((i for i in range(2, len(self.buffer)) if 0x40 <= self.buffer[i] <= 0x7e), None)
            if end is None:
                if len(self.buffer) > 96:
                    self.buffer.clear()
                break
            sequence = bytes(self.buffer[:end + 1])
            del self.buffer[:end + 1]
            event = parse_kitty_key(sequence)
            if event is None and re.fullmatch(rb'\x1b\[[0-9;]*[ABCD]', sequence):
                event = KeyEvent(ARROW_KEYS[sequence[-1]])
            if event is not None:
                events.append(event)
        return events

    def read_events(self) -> list[KeyEvent]:
        events, self.pending = self.pending, []
        while select.select([sys.stdin], [], [], 0.0)[0]:
            chunk = os.read(sys.stdin.fileno(), 128)
            if not chunk:
                break
            events.extend(self.feed(chunk))
        return events
