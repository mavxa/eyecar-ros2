"""Decode the EyeCar firmware's raw US and IR telemetry."""


def parse_sensor_line(line: str) -> tuple[str, list[int]] | None:
    fields = line.split()
    if not fields or fields[0] not in ('US', 'IR'):
        return None
    kind = fields[0]
    count, maximum = (4, 400) if kind == 'US' else (5, 1023)
    if len(fields) != count + 1:
        raise ValueError(f'{kind} requires {count} readings')
    values = [int(field) for field in fields[1:]]
    if any(value < 0 or value > maximum for value in values):
        raise ValueError(f'{kind} readings must be within 0..{maximum}')
    return kind, values
