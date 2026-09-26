from __future__ import annotations

from typing import Any

from eyecar_interfaces.msg import LedState, LedStateArray
from eyecar_interfaces.srv import SetLeds
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import ColorRGBA, UInt8


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class LedStripNode(Node):
    """Drive a WS2812/SK6812 strip as a whole or pixel by pixel."""

    def __init__(self) -> None:
        super().__init__('eyecar_led_driver')

        self.declare_parameter('gpio_pin', 18)
        self.declare_parameter('led_count', 12)
        self.declare_parameter('brightness', 64)
        self.declare_parameter('frequency_hz', 800_000)
        self.declare_parameter('dma_channel', 10)
        self.declare_parameter('invert_signal', False)
        self.declare_parameter('pwm_channel', 0)
        self.declare_parameter('clear_on_shutdown', True)

        self.gpio_pin = int(self.get_parameter('gpio_pin').value)
        self.led_count = int(self.get_parameter('led_count').value)
        self.brightness = int(self.get_parameter('brightness').value)
        frequency_hz = int(self.get_parameter('frequency_hz').value)
        dma_channel = int(self.get_parameter('dma_channel').value)
        invert_signal = bool(self.get_parameter('invert_signal').value)
        pwm_channel = int(self.get_parameter('pwm_channel').value)
        self.clear_on_shutdown = bool(
            self.get_parameter('clear_on_shutdown').value
        )

        if self.led_count <= 0:
            raise ValueError('led_count must be greater than zero')
        if not 0 <= self.brightness <= 255:
            raise ValueError('brightness must be between 0 and 255')

        try:
            from rpi_ws281x import PixelStrip
        except ImportError as exc:
            raise RuntimeError(
                'rpi_ws281x is missing; install python3-rpi-ws281x'
            ) from exc

        self.strip: Any = PixelStrip(
            self.led_count,
            self.gpio_pin,
            freq_hz=frequency_hz,
            dma=dma_channel,
            invert=invert_signal,
            brightness=self.brightness,
            channel=pwm_channel,
        )
        self.strip.begin()
        self.pixel_rgb = [(0, 0, 0) for _ in range(self.led_count)]
        self._closed = False

        state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.state_publisher = self.create_publisher(
            LedStateArray,
            '/eyecar/led/state',
            state_qos,
        )
        self.brightness_state_publisher = self.create_publisher(
            UInt8,
            '/eyecar/led/brightness_state',
            state_qos,
        )
        self.color_subscription = self.create_subscription(
            ColorRGBA,
            '/eyecar/led/color',
            self.set_color,
            10,
        )
        self.brightness_subscription = self.create_subscription(
            UInt8,
            '/eyecar/led/brightness',
            self.set_brightness,
            10,
        )
        self.set_leds_service = self.create_service(
            SetLeds,
            '/eyecar/led/set_leds',
            self.set_leds,
        )

        self._render()
        self._publish_state()
        self.get_logger().info(
            f'WS281x ready: BCM GPIO{self.gpio_pin}, '
            f'{self.led_count} pixel(s), brightness={self.brightness}'
        )

    @staticmethod
    def _component(value: float) -> int:
        return round(clamp(float(value), 0.0, 1.0) * 255)

    def set_color(self, message: ColorRGBA) -> None:
        color = (
            self._component(message.r),
            self._component(message.g),
            self._component(message.b),
        )
        self.pixel_rgb = [color for _ in range(self.led_count)]
        self._render()
        self._publish_led_state()
        self.get_logger().info(
            f'LED fill: r={color[0]} g={color[1]} b={color[2]}'
        )

    def set_leds(
        self,
        request: SetLeds.Request,
        response: SetLeds.Response,
    ) -> SetLeds.Response:
        invalid_indices = sorted(
            {int(led.index) for led in request.leds}
            - set(range(self.led_count))
        )
        if invalid_indices:
            response.success = False
            response.message = (
                f'indices outside 0..{self.led_count - 1}: '
                + ', '.join(map(str, invalid_indices))
            )
            return response

        for led in request.leds:
            self.pixel_rgb[int(led.index)] = (
                int(led.r),
                int(led.g),
                int(led.b),
            )

        self._render()
        self._publish_led_state()
        response.success = True
        response.message = f'updated {len(request.leds)} LED(s)'
        return response

    def set_brightness(self, message: UInt8) -> None:
        self.brightness = int(message.data)
        self.strip.setBrightness(self.brightness)
        self._render()
        self._publish_brightness_state()
        self.get_logger().info(f'LED brightness: {self.brightness}')

    def _render(self) -> None:
        for index, (red, green, blue) in enumerate(self.pixel_rgb):
            self.strip.setPixelColorRGB(index, red, green, blue)
        self.strip.show()

    def _publish_led_state(self) -> None:
        message = LedStateArray()
        message.leds = [
            LedState(index=index, r=red, g=green, b=blue)
            for index, (red, green, blue) in enumerate(self.pixel_rgb)
        ]
        self.state_publisher.publish(message)

    def _publish_brightness_state(self) -> None:
        message = UInt8()
        message.data = self.brightness
        self.brightness_state_publisher.publish(message)

    def _publish_state(self) -> None:
        self._publish_led_state()
        self._publish_brightness_state()

    def shutdown_strip(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.clear_on_shutdown:
            self.pixel_rgb = [(0, 0, 0) for _ in range(self.led_count)]
            try:
                self._render()
            except Exception as exc:  # hardware shutdown must continue
                self.get_logger().warning(f'Failed to clear LED strip: {exc}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = LedStripNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.shutdown_strip()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
