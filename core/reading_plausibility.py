"""
Plausibility checks for sensor readings (configurable via Django settings).

Used at ingest, in map API display logic, and for ice-warning updates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

MEASUREMENT_STATUS_OK = 'ok'
MEASUREMENT_STATUS_UNRELIABLE = 'unreliable'
MEASUREMENT_STATUS_MAINTENANCE = 'maintenance'

STATUS_MESSAGE_MAINTENANCE = 'Sensor gerade in Wartung'
STATUS_MESSAGE_UNRELIABLE = 'Aktueller Messwert nicht plausibel'


@dataclass(frozen=True)
class PlausibilityLimits:
    road_temp_min: float
    road_temp_max: float
    air_temp_min: float
    air_temp_max: float
    humidity_min: float
    humidity_max: float


def get_plausibility_limits() -> PlausibilityLimits:
    cfg: dict[str, Any] = getattr(settings, 'READING_PLAUSIBILITY', {})
    return PlausibilityLimits(
        road_temp_min=float(cfg.get('road_temp_min', -50.0)),
        road_temp_max=float(cfg.get('road_temp_max', 60.0)),
        air_temp_min=float(cfg.get('air_temp_min', -50.0)),
        air_temp_max=float(cfg.get('air_temp_max', 50.0)),
        humidity_min=float(cfg.get('humidity_min', 0.0)),
        humidity_max=float(cfg.get('humidity_max', 100.0)),
    )


def is_reading_plausible(
    *,
    road_temperature: float,
    air_temperature: float,
    humidity: float,
    limits: PlausibilityLimits | None = None,
) -> bool:
    limits = limits or get_plausibility_limits()
    if not limits.road_temp_min <= road_temperature <= limits.road_temp_max:
        return False
    if not limits.air_temp_min <= air_temperature <= limits.air_temp_max:
        return False
    if not limits.humidity_min <= humidity <= limits.humidity_max:
        return False
    return True


def reading_instance_plausible(reading: Any, *, limits: PlausibilityLimits | None = None) -> bool:
    if getattr(reading, 'is_plausible', True) is False:
        return False
    return is_reading_plausible(
        road_temperature=reading.road_temperature,
        air_temperature=reading.air_temperature,
        humidity=reading.humidity,
        limits=limits,
    )
