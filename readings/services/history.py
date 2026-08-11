from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.ice_warning import alert_status_for_level, evaluate_ice_warning
from core.utils import calculate_dew_point
from readings.models import SensorReading
from sensors.models import Sensor

MAX_HISTORY_DAYS = 14


class HistoryRangeError(Exception):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


def parse_history_timestamp(value: str, field: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise HistoryRangeError(f'Invalid {field} timestamp. Use ISO 8601 format.', field=field)
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.utc)
    return parsed


def resolve_history_range(
    *,
    days: int | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
) -> tuple[datetime, datetime, int]:
    now = timezone.now()

    if time_from or time_to:
        if not time_from or not time_to:
            raise HistoryRangeError(
                'Provide both from and to when using an explicit time range.',
                field='from',
            )
        start = parse_history_timestamp(time_from, 'from')
        end = parse_history_timestamp(time_to, 'to')
        if end <= start:
            raise HistoryRangeError('to must be after from.', field='to')
    else:
        selected_days = days if days is not None else 7
        if selected_days < 1 or selected_days > MAX_HISTORY_DAYS:
            raise HistoryRangeError(
                f'days must be between 1 and {MAX_HISTORY_DAYS}.',
                field='days',
            )
        end = now
        start = now - timedelta(days=selected_days)
        return start, end, selected_days

    span_days = (end - start).total_seconds() / 86400
    if span_days > MAX_HISTORY_DAYS:
        raise HistoryRangeError(
            f'Time range must not exceed {MAX_HISTORY_DAYS} days.',
            field='to',
        )

    return start, end, max(1, int(span_days) if span_days.is_integer() else int(span_days) + 1)


def reading_history_points(sensor_id: int, start: datetime, end: datetime) -> tuple[list[dict], Sensor]:
    sensor = Sensor.objects.filter(id=sensor_id, active=True).select_related('municipality').first()
    if not sensor:
        raise HistoryRangeError('Sensor not found.', field='sensor')

    readings = (
        SensorReading.objects.filter(sensor_id=sensor_id, timestamp__gte=start, timestamp__lte=end)
        .order_by('timestamp')
        .only(
            'timestamp',
            'air_temperature',
            'road_temperature',
            'humidity',
            'air_temperature_radiation_shield',
            'air_humidity_radiation_shield',
            'air_temperature_unshielded',
            'air_humidity_unshielded',
            'reported_dew_point',
            'angle',
            'sensor_temperature',
            'battery_voltage',
        )
    )

    points = []
    for reading in readings:
        dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
        ice_warning_level = evaluate_ice_warning(
            reading.road_temperature,
            dew_point,
            reading.humidity,
        )
        points.append(
            {
                'timestamp': reading.timestamp,
                'air_temperature': reading.air_temperature,
                'road_temperature': reading.road_temperature,
                'humidity': reading.humidity,
                'air_temperature_radiation_shield': reading.air_temperature_radiation_shield,
                'air_humidity_radiation_shield': reading.air_humidity_radiation_shield,
                'air_temperature_unshielded': reading.air_temperature_unshielded,
                'air_humidity_unshielded': reading.air_humidity_unshielded,
                'dew_point': dew_point,
                'reported_dew_point': reading.reported_dew_point,
                'angle': reading.angle,
                'sensor_temperature': reading.sensor_temperature,
                'battery_voltage': reading.battery_voltage,
                'ice_warning_level': ice_warning_level,
                'alert_status': alert_status_for_level(ice_warning_level),
            }
        )

    return points, sensor


def build_reading_history(
    *,
    sensor_id: int,
    days: int | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
) -> dict:
    start, end, selected_days = resolve_history_range(
        days=days,
        time_from=time_from,
        time_to=time_to,
    )
    points, sensor = reading_history_points(sensor_id, start, end)
    sensor_name = sensor.display_name or sensor.name

    return {
        'sensor_id': sensor.id,
        'sensor_name': sensor_name,
        'from': start,
        'to': end,
        'days': selected_days,
        'count': len(points),
        'points': points,
    }
