from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScaleMeasurement:
    weight: float
    impedance: int
    scale_datetime: datetime | None  # date/time reported by the scale itself


@dataclass
class BodyCompositionMessage:
    stabilized: bool
    measurement: ScaleMeasurement


def parse_scale_measurement(buffer: bytearray) -> ScaleMeasurement:
    weight = ((buffer[12] << 8) + buffer[11]) / 200
    impedance = (buffer[10] << 8) + buffer[9]

    # Bytes 2-3: year, 4: month, 5: day, 6: hour, 7: minute, 8: second
    try:
        year = (buffer[3] << 8) + buffer[2]
        scale_datetime = datetime(year, buffer[4], buffer[5], buffer[6], buffer[7], buffer[8])
    except Exception:
        scale_datetime = None

    return ScaleMeasurement(weight=weight, impedance=impedance, scale_datetime=scale_datetime)


def parse_body_composition_message(buffer: bytearray) -> BodyCompositionMessage:
    stabilized = (buffer[1] & 32) > 0
    measurement = parse_scale_measurement(buffer)

    return BodyCompositionMessage(stabilized=stabilized, measurement=measurement)
