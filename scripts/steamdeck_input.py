#!/usr/bin/env python3
import argparse
import json
import os
import select
import struct
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='/dev/input/js0')
    parser.add_argument('--throttle-axis', type=int, default=1)
    parser.add_argument('--steering-axis', type=int, default=0)
    parser.add_argument('--enable-button', type=int, default=4)
    parser.add_argument('--stop-button', type=int, default=1)
    parser.add_argument('--throttle-sign', type=int, choices=(-1, 1), default=-1)
    parser.add_argument('--steering-sign', type=int, choices=(-1, 1), default=-1)
    parser.add_argument('--inspect', action='store_true', help='print events; do not send commands')
    args = parser.parse_args()
    if min(args.throttle_axis, args.steering_axis, args.enable_button, args.stop_button) < 0:
        parser.error('axis/button indices must be nonnegative')
    if args.enable_button == args.stop_button:
        parser.error('enable and stop must be different buttons')
    axes, buttons = {}, {}
    fd = None
    try:
        fd = os.open(args.device, os.O_RDONLY | os.O_NONBLOCK)
        print(f'Reading {args.device}; use --inspect to verify axis/button numbers', file=sys.stderr)
        next_send = time.monotonic()
        while True:
            select.select([fd], [], [], max(0, next_send - time.monotonic()))
            # Drain queued events before producing the next heartbeat.
            for _ in range(128):
                try:
                    data = os.read(fd, 8)
                except BlockingIOError:
                    break
                if len(data) != 8:
                    raise OSError('controller disconnected or incomplete joystick event')
                _, value, kind, number = struct.unpack('=IhBB', data)
                initial = bool(kind & 0x80)
                kind &= ~0x80
                if kind == 2:
                    axes[number] = max(-1.0, min(1.0, value / 32767.0))
                elif kind == 1:
                    buttons[number] = bool(value)
                if args.inspect:
                    print(f'{"axis" if kind == 2 else "button"} {number}: {value}'
                          f'{" (initial)" if initial else ""}', flush=True)
            now = time.monotonic()
            if now >= next_send:
                if not args.inspect:
                    mapped = (args.throttle_axis in axes and args.steering_axis in axes
                              and args.enable_button in buttons and args.stop_button in buttons)
                    packet = {
                        'throttle': args.throttle_sign * axes.get(args.throttle_axis, 0.0),
                        'steering': args.steering_sign * axes.get(args.steering_axis, 0.0),
                        'enabled': mapped and buttons.get(args.enable_button, False),
                        'stop': buttons.get(args.stop_button, False),
                    }
                    print(json.dumps(packet, separators=(',', ':')), flush=True)
                next_send = now + 0.05
    except KeyboardInterrupt:
        pass
    except (OSError, BrokenPipeError) as error:
        print(f'Gamepad input stopped: {error}', file=sys.stderr)
        return 1
    finally:
        if not args.inspect:
            try:
                print('{"throttle":0,"steering":0,"enabled":false,"stop":true}', flush=True)
            except (BrokenPipeError, OSError):
                pass
        if fd is not None:
            os.close(fd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
