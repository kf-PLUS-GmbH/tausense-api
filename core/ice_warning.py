"""
Ice / slip warning levels (Advisory → Critical) with separate reset (hysteresis) thresholds.

Trigger (activation) uses evaluate_ice_warning(); the active map colour uses
transition_ice_warning_level() so levels do not flicker at the boundary.

Levels:
- Advisory (yellow): T_road <= 2.0 °C and |T_road - Td| <= 2.0 °C
  Reset: T_road > 2.5 °C
- Warning (orange): T_road <= 1.0 °C and |T_road - Td| <= 1.0 °C,
  or RH >= 90 % and T_road <= 1.5 °C
  Reset: T_road > 1.5 °C
- Critical (red): T_road <= 0.0 °C and |T_road - Td| <= 0.5 °C,
  or T_road <= 0.0 °C and precipitation detected
  Reset: T_road > 0.5 °C for at least 10 minutes (all readings in window)
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterable

ICE_WARNING_NONE = 'none'
ICE_WARNING_POSSIBLE_SLIP = 'possible_slip'
ICE_WARNING_INCREASED_ICE = 'increased_ice'
ICE_WARNING_ACUTE_ICE = 'acute_ice'

ICE_WARNING_LEVELS = (
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_ACUTE_ICE,
)

ICE_WARNING_LABELS = {
    ICE_WARNING_NONE: 'Keine Warnung',
    ICE_WARNING_POSSIBLE_SLIP: 'Mögliche Rutschgefahr',
    ICE_WARNING_INCREASED_ICE: 'Erhöhte Eisgefahr',
    ICE_WARNING_ACUTE_ICE: 'Akute Eisbildung wahrscheinlich',
}

ALERT_STATUS_BY_LEVEL = {
    ICE_WARNING_NONE: 'green',
    ICE_WARNING_POSSIBLE_SLIP: 'yellow',
    ICE_WARNING_INCREASED_ICE: 'orange',
    ICE_WARNING_ACUTE_ICE: 'red',
}

ICE_WARNING_SEVERITY = {
    ICE_WARNING_NONE: 0,
    ICE_WARNING_POSSIBLE_SLIP: 1,
    ICE_WARNING_INCREASED_ICE: 2,
    ICE_WARNING_ACUTE_ICE: 3,
}

RESET_ROAD_POSSIBLE_SLIP = 2.5
RESET_ROAD_INCREASED_ICE = 1.5
RESET_ROAD_ACUTE_ICE = 0.5
ACUTE_RESET_STABLE_MINUTES = 10

PRECIPITATION_RAW_KEYS = (
    'precipitation',
    'precipitation_detected',
    'rain',
    'rain_detected',
    'rainfall',
    'niederschlag',
    'has_precipitation',
)


def precipitation_detected(raw_data: dict[str, Any] | None) -> bool:
    if not isinstance(raw_data, dict):
        return False
    for key in PRECIPITATION_RAW_KEYS:
        value = raw_data.get(key)
        if _truthy_sensor_flag(value):
            return True
    for nested_key in ('data', 'object', 'payload', 'decoded'):
        nested = raw_data.get(nested_key)
        if isinstance(nested, dict) and precipitation_detected(nested):
            return True
    return False


def _truthy_sensor_flag(value: Any) -> bool:
    if value is True or value == 1:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on', 'detected'}
    return False


def evaluate_ice_warning(
    road_temperature: float,
    dew_point: float,
    humidity: float,
    *,
    precipitation: bool = False,
) -> str:
    """
    Instantaneous trigger level from the current measurement (most severe wins).
    """
    diff = abs(road_temperature - dew_point)

    if road_temperature <= 0.0 and (diff <= 0.5 or precipitation):
        return ICE_WARNING_ACUTE_ICE

    if (road_temperature <= 1.0 and diff <= 1.0) or (
        humidity >= 90.0 and road_temperature <= 1.5
    ):
        return ICE_WARNING_INCREASED_ICE

    if road_temperature <= 2.0 and diff <= 2.0:
        return ICE_WARNING_POSSIBLE_SLIP

    return ICE_WARNING_NONE


def _reset_possible_slip(road_temperature: float) -> bool:
    return road_temperature > RESET_ROAD_POSSIBLE_SLIP


def _reset_increased_ice(road_temperature: float) -> bool:
    return road_temperature > RESET_ROAD_INCREASED_ICE


def _reading_road(reading) -> float:
    return float(reading.road_temperature)


def _acute_reset_confirmed(road_temperature: float, recent_readings: Iterable) -> bool:
    if road_temperature <= RESET_ROAD_ACUTE_ICE:
        return False
    readings = list(recent_readings)
    if not readings:
        return False
    for item in readings:
        if _reading_road(item) <= RESET_ROAD_ACUTE_ICE:
            return False
    span = readings[-1].timestamp - readings[0].timestamp
    return span >= timedelta(minutes=ACUTE_RESET_STABLE_MINUTES)


def _stored_level_cleared(
    stored_level: str,
    road_temperature: float,
    recent_readings: Iterable,
) -> bool:
    if stored_level == ICE_WARNING_POSSIBLE_SLIP:
        return _reset_possible_slip(road_temperature)
    if stored_level == ICE_WARNING_INCREASED_ICE:
        return _reset_increased_ice(road_temperature)
    if stored_level == ICE_WARNING_ACUTE_ICE:
        return _acute_reset_confirmed(road_temperature, recent_readings)
    return True


def transition_ice_warning_level(
    *,
    stored_level: str,
    road_temperature: float,
    air_temperature: float,
    humidity: float,
    dew_point: float | None = None,
    precipitation: bool = False,
    recent_readings: Iterable | None = None,
) -> str:
    """
    Apply hysteresis: escalate immediately on trigger; downgrade only after reset.
    """
    if dew_point is None:
        from core.utils import calculate_dew_point

        dew_point = calculate_dew_point(air_temperature, humidity)

    triggered = evaluate_ice_warning(
        road_temperature,
        dew_point,
        humidity,
        precipitation=precipitation,
    )
    stored_level = stored_level or ICE_WARNING_NONE
    recent_readings = recent_readings or []

    if ICE_WARNING_SEVERITY[triggered] > ICE_WARNING_SEVERITY[stored_level]:
        return triggered

    if stored_level == ICE_WARNING_NONE:
        return ICE_WARNING_NONE

    if not _stored_level_cleared(stored_level, road_temperature, recent_readings):
        return stored_level

    return triggered


def alert_status_for_level(level: str) -> str:
    return ALERT_STATUS_BY_LEVEL.get(level, 'gray')
