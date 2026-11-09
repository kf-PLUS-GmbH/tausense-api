"""Map / API display helpers: latest vs display reading, measurement status."""
from __future__ import annotations

from typing import Any

from core.ice_warning import ICE_WARNING_LABELS, ICE_WARNING_NONE, alert_status_for_level
from core.reading_plausibility import (
    MEASUREMENT_STATUS_MAINTENANCE,
    MEASUREMENT_STATUS_OK,
    MEASUREMENT_STATUS_UNRELIABLE,
    STATUS_MESSAGE_MAINTENANCE,
    STATUS_MESSAGE_UNRELIABLE,
    reading_instance_plausible,
)
from core.utils import calculate_dew_point, calculate_trend
from readings.models import SensorReading
from sensors.models import Sensor


def _reading_payload(
    reading: SensorReading,
    *,
    previous_air: float | None,
    include_extended_fields: bool = True,
) -> dict[str, Any]:
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    payload: dict[str, Any] = {
        'timestamp': reading.timestamp,
        'device_name': reading.device_name,
        'air_temperature': reading.air_temperature,
        'road_temperature': reading.road_temperature,
        'humidity': reading.humidity,
        'dew_point': dew_point,
        'trend': calculate_trend(reading.air_temperature, previous_air),
        'is_plausible': reading_instance_plausible(reading),
    }
    if include_extended_fields:
        payload.update(
            {
                'air_temperature_radiation_shield': reading.air_temperature_radiation_shield,
                'air_humidity_radiation_shield': reading.air_humidity_radiation_shield,
                'air_temperature_unshielded': reading.air_temperature_unshielded,
                'air_humidity_unshielded': reading.air_humidity_unshielded,
                'reported_dew_point': reading.reported_dew_point,
                'angle': reading.angle,
                'sensor_temperature': reading.sensor_temperature,
                'battery_voltage': reading.battery_voltage,
            }
        )
    return payload


def resolve_map_measurement_context(
    sensor: Sensor,
    latest: SensorReading | None,
    latest_plausible: SensorReading | None,
    *,
    previous_air_for_display: float | None,
) -> dict[str, Any]:
    """
    Build measurement_status, status_message, latest_reading, display_reading, alert UI fields.
    """
    if sensor.maintenance_mode:
        display = latest_plausible
        return _build_context(
            sensor=sensor,
            latest=latest,
            display=display,
            measurement_status=MEASUREMENT_STATUS_MAINTENANCE,
            status_message=STATUS_MESSAGE_MAINTENANCE,
            previous_air=previous_air_for_display,
        )

    if latest is None:
        return _build_context(
            sensor=sensor,
            latest=None,
            display=None,
            measurement_status=MEASUREMENT_STATUS_OK,
            status_message=None,
            previous_air=None,
        )

    latest_ok = reading_instance_plausible(latest)
    if latest_ok:
        return _build_context(
            sensor=sensor,
            latest=latest,
            display=latest,
            measurement_status=MEASUREMENT_STATUS_OK,
            status_message=None,
            previous_air=getattr(latest, 'previous_air_temperature', None),
        )

    display = latest_plausible
    return _build_context(
        sensor=sensor,
        latest=latest,
        display=display,
        measurement_status=MEASUREMENT_STATUS_UNRELIABLE,
        status_message=STATUS_MESSAGE_UNRELIABLE,
        previous_air=previous_air_for_display,
    )


def _build_context(
    *,
    sensor: Sensor,
    latest: SensorReading | None,
    display: SensorReading | None,
    measurement_status: str,
    status_message: str | None,
    previous_air: float | None,
) -> dict[str, Any]:
    ice_level = sensor.ice_warning_level or ICE_WARNING_NONE
    if measurement_status != MEASUREMENT_STATUS_OK and display is None:
        ice_level = ICE_WARNING_NONE
        alert_status = 'gray'
    elif measurement_status == MEASUREMENT_STATUS_MAINTENANCE:
        ice_level = ICE_WARNING_NONE
        alert_status = 'gray'
    else:
        alert_status = alert_status_for_level(ice_level)

    latest_payload = (
        _reading_payload(latest, previous_air=getattr(latest, 'previous_air_temperature', None))
        if latest
        else None
    )
    display_payload = None
    if display is not None:
        is_stale = latest is not None and display.id != latest.id
        display_payload = _reading_payload(display, previous_air=previous_air)
        display_payload['is_stale'] = is_stale

    return {
        'measurement_status': measurement_status,
        'status_message': status_message,
        'latest_reading': latest_payload,
        'display_reading': display_payload,
        'ice_warning_level': ice_level,
        'ice_warning_label': ICE_WARNING_LABELS[ice_level],
        'alert_status': alert_status,
    }
