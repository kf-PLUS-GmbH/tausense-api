from datetime import timedelta

from django.utils import timezone

from core.ice_warning import (
    ICE_WARNING_NONE,
    precipitation_detected,
    transition_ice_warning_level,
)
from core.utils import calculate_dew_point
from readings.models import SensorReading


def _recent_readings(sensor, reading: SensorReading, *, minutes: int = 10):
    window_start = reading.timestamp - timedelta(minutes=minutes)
    return (
        SensorReading.objects.filter(
            sensor=sensor,
            timestamp__lte=reading.timestamp,
            timestamp__gte=window_start,
        )
        .order_by('timestamp')
    )


def update_sensor_ice_warning_from_reading(sensor, reading: SensorReading) -> str:
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    precip = precipitation_detected(raw_data=reading.raw_data)
    recent = _recent_readings(sensor, reading, minutes=10)

    new_level = transition_ice_warning_level(
        stored_level=sensor.ice_warning_level or ICE_WARNING_NONE,
        road_temperature=reading.road_temperature,
        air_temperature=reading.air_temperature,
        humidity=reading.humidity,
        precipitation=precip,
        dew_point=dew_point,
        recent_readings=recent,
    )

    if new_level != (sensor.ice_warning_level or ICE_WARNING_NONE):
        sensor.ice_warning_level = new_level
        sensor.ice_warning_level_since = reading.timestamp
        sensor.save(
            update_fields=['ice_warning_level', 'ice_warning_level_since', 'updated_at'],
        )
    return new_level


def ice_warning_level_for_reading(reading: SensorReading) -> str:
    sensor = reading.sensor
    latest = (
        SensorReading.objects.filter(sensor=sensor)
        .order_by('-timestamp')
        .values_list('id', flat=True)
        .first()
    )
    if latest == reading.id:
        return update_sensor_ice_warning_from_reading(sensor, reading)
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    return transition_ice_warning_level(
        stored_level=ICE_WARNING_NONE,
        road_temperature=reading.road_temperature,
        air_temperature=reading.air_temperature,
        humidity=reading.humidity,
        precipitation=precipitation_detected(raw_data=reading.raw_data),
        dew_point=dew_point,
        recent_readings=[reading],
    )
