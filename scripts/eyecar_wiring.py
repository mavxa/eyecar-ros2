#!/usr/bin/env python3
"""Generate the wiring references from the checked-in firmware and LED defaults."""

import argparse
import ast
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BLUE, GREEN, RED, INK = '#075b91', '#237f79', '#b64336', '#182c3a'
PI_ROWS = [
    ('3V3', '5V'), ('GPIO2 / SDA1', '5V'), ('GPIO3 / SCL1', 'GND'),
    ('GPIO4', 'GPIO14 / TXD0'), ('GND', 'GPIO15 / RXD0'), ('GPIO17', 'GPIO18'),
    ('GPIO27', 'GND'), ('GPIO22', 'GPIO23'), ('3V3', 'GPIO24'),
    ('GPIO10 / MOSI', 'GND'), ('GPIO9 / MISO', 'GPIO25'), ('GPIO11 / SCLK', 'GPIO8 / CE0'),
    ('GND', 'GPIO7 / CE1'), ('GPIO0 / ID_SD', 'GPIO1 / ID_SC'), ('GPIO5', 'GND'),
    ('GPIO6', 'GPIO12'), ('GPIO13', 'GND'), ('GPIO19', 'GPIO16'),
    ('GPIO26', 'GPIO20'), ('GND', 'GPIO21'),
]


def pinmap(firmware, led_source):
    constants = {name: int(value) for name, value in re.findall(
        r'constexpr\s+uint8_t\s+(\w+)\s*=\s*(\d+)\s*;', firmware)}
    values = {'motor': constants['MOTOR_PIN'], 'steering': constants['STEERING_PIN']}
    values['ultrasonic'] = [(constants[f'US{i}_TRIG_PIN'], constants[f'US{i}_ECHO_PIN'])
                            for i in range(1, 5)]
    analog = re.search(r'IR_PINS\[\]\s*=\s*\{([^}]+)\}', firmware)
    values['infrared'] = re.findall(r'\bA\d+\b', analog.group(1))
    defaults = {}
    for node in ast.walk(ast.parse(led_source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'declare_parameter' and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant)):
            defaults[node.args[0].value] = node.args[1].value
    values['led_gpio'], values['led_count'] = defaults['gpio_pin'], defaults['led_count']
    pins = [values['motor'], values['steering'], *[p for pair in values['ultrasonic'] for p in pair]]
    if len(pins) != len(set(pins)) or any(not 0 <= p <= 53 for p in pins):
        raise ValueError('Conflicting or invalid Mega digital pins')
    if len(values['infrared']) != len(set(values['infrared'])):
        raise ValueError('Duplicate analog inputs')
    values['led_physical'] = next(2 * row + col + 1 for row, pair in enumerate(PI_ROWS)
                                  for col, label in enumerate(pair)
                                  if label.split(' / ')[0] == f'GPIO{values["led_gpio"]}')
    return values


def text(x, y, label, size=18, color=INK, anchor='start', weight='normal'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(str(label))}</text>')


def box(x, y, width, height, title, lines=()):
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="5" '
            f'fill="#fff" stroke="#b6c5cc" stroke-width="2"/>'
            + text(x + 18, y + 31, title, 20, BLUE, weight='bold')
            + ''.join(text(x + 18, y + 62 + i * 25, line, 17) for i, line in enumerate(lines)))


def wire(points, color=BLUE):
    return (f'<path d="{points}" fill="none" stroke="{color}" stroke-width="3" '
            f'marker-end="url(#{color[1:]})"/>')


def page(title, subtitle, height, content):
    markers = ''.join(f'<marker id="{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                      f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
                      f'<path d="M0 0L10 5L0 10Z" fill="{c}"/></marker>' for c in (BLUE, GREEN, RED))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" '
            f'viewBox="0 0 1280 {height}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><defs>{markers}</defs>'
            f'<rect width="1280" height="{height}" fill="#f6f8fa"/>'
            '<g font-family="DejaVu Sans,Arial,sans-serif">'
            + text(40, 54, title, 32, BLUE, weight='bold')
            + text(40, 90, subtitle, 18)
            + '<path d="M40 116H1240" stroke="#075b91" stroke-width="2"/>'
            + ''.join(content) + '</g></svg>\n')


def mega_diagram(p):
    body = [box(440, 170, 380, 635, 'Arduino Mega 2560', ['USB: 115200 baud']),
            box(40, 230, 290, 110, 'Motor driver / ESC', ['Signal input only', 'Power follows the ESC rating']),
            box(40, 390, 290, 110, 'Steering servo', ['Signal input only', 'Keep its rated power supply']),
            text(465, 290, f'D{p["motor"]} / S{p["motor"]}', 22, BLUE, weight='bold'),
            text(465, 450, f'D{p["steering"]} / S{p["steering"]}', 22, BLUE, weight='bold'),
            wire('M440 285H330'), wire('M440 445H330')]
    for i, ((trig, echo), position) in enumerate(zip(p['ultrasonic'], ('rear', 'right', 'left', 'front'))):
        y = 170 + i * 145
        body.extend([box(940, y, 300, 112, f'US{i + 1}: {position}', ['HC-SR04', '+5V and GND required']),
                     text(635, y + 49, f'D{trig}  TRIG', 18, BLUE),
                     text(635, y + 82, f'D{echo}  ECHO', 18, GREEN),
                     wire(f'M820 {y + 45}H940'), wire(f'M940 {y + 78}H820', GREEN)])
    body.extend([text(465, 745, 'Analog inputs', 20, BLUE, weight='bold'),
                 text(465, 778, ' / '.join(p['infrared']), 21),
                 box(350, 860, 580, 110, f'{len(p["infrared"])} IR channels',
                     ['Module AO outputs to A0-A4 in connector order.', 'Firmware reads raw ADC values from 0 to 1023.']),
                 wire('M640 860V805', GREEN),
                 text(40, 1015, 'Signal map, not a physical header layout. S2/S3 mean the shield signal row.', 17),
                 text(40, 1047, 'Sensor direction follows the project mapping; verify each channel on the actual rover.', 17)])
    return page('EyeCar / Mega signal map', 'Pin numbers are extracted from eyecar_base_controller.ino.', 1080, body)


def pi_diagram(p):
    body = [box(530, 170, 220, 800, '40-pin header'),
            box(40, 190, 270, 170, 'Pi 4 Model B power', ['USB-C from regulated 5V.', 'Supply target: 3A for Pi 4.', '5V header pins are shown', 'for reference, not used here.']),
            box(40, 460, 270, 145, 'USB connections', ['Pi USB-A to Mega USB-B.', 'Camera to another USB port.', 'No GPIO UART cable.']),
            box(40, 720, 270, 160, 'Numbering', [f'{p["led_physical"]}: physical header position.', f'GPIO{p["led_gpio"]}: BCM identifier.', f'{p["led_count"]}: LED pixel count.', 'These are different numbers.']),
            box(980, 310, 260, 185, 'LED data', [f'Pin {p["led_physical"]} / BCM GPIO{p["led_gpio"]}', '3.3V to 5V logic buffer', 'then strip DIN.', 'See overview diagram.']),
            box(980, 620, 260, 160, 'Common ground', ['Use pin 6 for GND.', 'To LED supply GND.', 'Other header GND pins', 'are the same ground.'])]
    for row, pair in enumerate(PI_ROWS):
        y = 235 + row * 36
        for col, label in enumerate(pair):
            number = row * 2 + col + 1
            selected = number == p['led_physical']
            color = GREEN if selected else RED if label in ('5V', '3V3') else '#586976' if label == 'GND' else BLUE
            cx = 575 if col == 0 else 705
            body.extend([f'<circle cx="{cx}" cy="{y}" r="13" fill="{color}"/>',
                         text(cx, y + 5, number, 13, '#fff', 'middle', 'bold'),
                         text(510 if col == 0 else 770, y + 6, label + (' / LED' if selected else ''),
                              17, color, 'end' if col == 0 else 'start', 'bold' if selected else 'normal')])
    body.extend([text(40, 1017, 'Top view of the header. Identify pin 1 from the PCB marking before connecting anything.', 18),
                 text(40, 1052, 'GPIO uses 3.3V logic. Never feed 5V into a GPIO signal pin.', 18, RED),
                 text(40, 1087, 'GPIO0 / GPIO1 are the HAT identification bus. Leave them unused in this build.', 17)])
    return page('EyeCar / Raspberry Pi 4 GPIO', 'BCM signal identifiers and physical header positions are shown separately.', 1130, body)


def overview(p):
    body = [box(40, 200, 240, 135, 'USB camera', ['UVC video over USB', 'Single capture process']),
            box(420, 200, 300, 180, 'Raspberry Pi 4', ['ROS 2 Jazzy / Linux', 'USB-A: camera and Mega', f'GPIO{p["led_gpio"]}: strip data', 'USB-C: regulated 5V input']),
            box(880, 200, 340, 160, 'Mega + expansion board', ['USB serial / 115200 baud', 'Firmware controls outputs', 'Sensor power: rated 5V rail']),
            wire('M280 265H420'), wire('M720 265H880'), text(748, 245, 'USB serial', 17, BLUE),
            box(880, 480, 340, 140, 'Motor driver + servo', [f'Motor signal: D{p["motor"]} / S{p["motor"]}', f'Steering signal: D{p["steering"]} / S{p["steering"]}', 'Keep the stock rated power path.']),
            wire('M1050 360V480'), text(1070, 430, 'Pulse signals', 17, BLUE),
            box(420, 480, 300, 135, '74AHCT125 buffer', ['Recommended for a 5V strip.', 'VCC = 5V; GND and OE = GND.', 'GPIO to A; Y to strip DIN.']),
            wire('M570 380V480'), text(590, 435, f'GPIO{p["led_gpio"]} / pin {p["led_physical"]}', 17, BLUE),
            box(40, 480, 240, 135, f'{p["led_count"]}-pixel LED strip', ['5V and common GND', 'Signal connects to DIN.', 'Observe the data arrows.']),
            wire('M420 545H280', GREEN), text(320, 525, 'Data', 17, GREEN),
            box(40, 730, 240, 135, '5V supply / BEC', ['BEC / power distribution', 'Check rating first.', 'No raw battery voltage.']),
            box(420, 730, 300, 160, 'HC-SR04 / IR inputs', ['4 HC-SR04 modules: 5V', f'{len(p["infrared"])} analog IR inputs', 'IR power: check module rating.', 'See the Mega signal map.']),
            wire('M720 795H800V325H880', GREEN),
            wire('M160 730V615', RED), wire('M280 795H330V410H500V380', RED),
            wire('M330 675H570V615', RED), wire('M330 795H420', RED),
            f'<circle cx="330" cy="675" r="5" fill="{RED}"/><circle cx="330" cy="795" r="5" fill="{RED}"/>',
            text(350, 708, 'Regulated 5V', 17, RED),
            '<path d="M40 924H1240" stroke="#586976" stroke-width="3"/>',
            text(40, 954, 'Common GND: Pi, Mega, sensors, LED supply and signal references.', 19),
            text(40, 1000, 'The buffer is recommended, not confirmed installed. Battery / ESC / VIN routing needs a hardware check.', 17)]
    return page('EyeCar / connection overview', 'Blue and green: data or control. Red: regulated 5V. Ground is shared.', 1040, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if the checked-in SVG references are stale')
    args = parser.parse_args()
    p = pinmap((ROOT / 'firmware/eyecar_base_controller/eyecar_base_controller.ino').read_text(),
               (ROOT / 'ros2_ws/src/eyecar_led/eyecar_led/led_strip.py').read_text())
    outputs = {'Mega signal map.svg': mega_diagram(p), 'Pi GPIO header.svg': pi_diagram(p),
               'Connection overview.svg': overview(p)}
    folder = ROOT / 'docs/images'
    if not args.check:
        folder.mkdir(parents=True, exist_ok=True)
    for name, svg in outputs.items():
        path = folder / name
        if args.check:
            if not path.exists() or path.read_text() != svg:
                raise SystemExit(f'Stale diagram: {path}. Run python3 scripts/eyecar_wiring.py')
        else:
            path.write_text(svg)
    print('Wiring references match the firmware and LED defaults.' if args.check else 'Generated 3 wiring references.')


if __name__ == '__main__':
    main()
