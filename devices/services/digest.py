from collections import Counter
from dataclasses import dataclass

from django.db.models import Q

from core.ice_warning import (
    ICE_WARNING_ACUTE_ICE,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_LABELS,
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
    ICE_WARNING_SEVERITY,
    alert_status_for_level,
)
from devices.models import AlertPreference
from sensors.models import Sensor


def _area_label_for_sensor(sensor: Sensor) -> str:
    """Kommune / Betreiber für Push-Titel (nicht Sensor-Standortname wie „Leupoldsgrün 1“)."""
    operator = (sensor.operator_name or '').strip()
    if operator:
        return operator
    if sensor.municipality_id:
        return sensor.municipality.name
    return ''


_LEVELS_FOR_DIGEST_BODY = (
    ICE_WARNING_ACUTE_ICE,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_POSSIBLE_SLIP,
)

# Kurztexte für Push-Body (Karte/App behalten ICE_WARNING_LABELS).
_PUSH_BODY_PREFIX = 'Glättehinweis: '
_PUSH_LEVEL_SHORT = {
    ICE_WARNING_ACUTE_ICE: 'sehr wahrscheinlich',
    ICE_WARNING_INCREASED_ICE: 'wahrscheinlich',
    ICE_WARNING_POSSIBLE_SLIP: 'möglich',
}


def _matches_severity_filter(severity_filter: str, alert_status: str) -> bool:
    if severity_filter == AlertPreference.SEVERITY_RED:
        return alert_status == 'red'
    if severity_filter == AlertPreference.SEVERITY_ORANGE:
        return alert_status in ('orange', 'red')
    return False


@dataclass(frozen=True)
class WarningSensorEntry:
    sensor_id: int
    sensor_name: str
    municipality_name: str
    level: str
    alert_status: str
    severity: int


def _sensoren_phrase(count: int) -> str:
    return '1 Sensor' if count == 1 else f'{count} Sensoren'


def _digest_body_for_warnings(warnings: list[WarningSensorEntry]) -> str:
    """Two-line push body: total sensors, then per-level counts."""
    count = len(warnings)
    by_level = Counter(entry.level for entry in warnings)
    active_levels = [level for level in _LEVELS_FOR_DIGEST_BODY if by_level.get(level, 0)]
    if not active_levels:
        return ICE_WARNING_LABELS[warnings[0].level]

    if len(active_levels) == 1:
        level = active_levels[0]
        detail = f'{by_level[level]} {_PUSH_LEVEL_SHORT[level]}'
    else:
        detail = ' · '.join(
            f'{by_level[level]} {_PUSH_LEVEL_SHORT[level]}' for level in active_levels
        )

    header = f'{_PUSH_BODY_PREFIX}{_sensoren_phrase(count)}'
    return f'{header}\n{detail}'


@dataclass(frozen=True)
class WarningDigest:
    type: str
    title: str
    body: str
    alert_status: str
    municipality_name: str
    sensor_count: int
    worst_level: str
    worst_severity: int
    sensors: tuple[WarningSensorEntry, ...]

    @property
    def sensor_ids(self) -> list[int]:
        return [entry.sensor_id for entry in self.sensors]

    @property
    def sensor_names(self) -> list[str]:
        return [entry.sensor_name for entry in self.sensors]

    @property
    def primary_sensor_id(self) -> int:
        return self.sensors[0].sensor_id


def get_subscribed_sensors(preference: AlertPreference):
    sensor_ids = preference.selected_sensor_ids or []
    selected_municipality = (preference.selected_municipality or '').strip()

    if not sensor_ids and not selected_municipality:
        return Sensor.objects.none()

    scope = Q()
    if sensor_ids:
        scope |= Q(id__in=sensor_ids)
    if selected_municipality:
        scope |= Q(municipality__name=selected_municipality) | Q(operator_name=selected_municipality)

    return (
        Sensor.objects.filter(active=True)
        .filter(scope)
        .select_related('municipality')
        .distinct()
    )


def collect_warning_sensors(preference: AlertPreference) -> list[WarningSensorEntry]:
    subscribed_ids = list(get_subscribed_sensors(preference).values_list('id', flat=True))
    if not subscribed_ids:
        return []

    warnings: list[WarningSensorEntry] = []
    sensors = (
        Sensor.objects.filter(id__in=subscribed_ids, active=True)
        .select_related('municipality')
        .only(
            'id',
            'name',
            'display_name',
            'operator_name',
            'ice_warning_level',
            'municipality_id',
            'municipality__name',
        )
    )

    for sensor in sensors:
        level = sensor.ice_warning_level or ICE_WARNING_NONE
        if level == ICE_WARNING_NONE:
            continue

        alert_status = alert_status_for_level(level)
        if not _matches_severity_filter(preference.severity_filter, alert_status):
            continue

        municipality_name = _area_label_for_sensor(sensor)
        warnings.append(
            WarningSensorEntry(
                sensor_id=sensor.id,
                sensor_name=sensor.display_name or sensor.name,
                municipality_name=municipality_name,
                level=level,
                alert_status=alert_status,
                severity=ICE_WARNING_SEVERITY[level],
            )
        )

    warnings.sort(key=lambda entry: entry.severity, reverse=True)
    return warnings


def build_warning_digest(preference: AlertPreference, warnings: list[WarningSensorEntry]) -> WarningDigest | None:
    if not warnings:
        return None

    worst = warnings[0]
    count = len(warnings)
    area_name = (preference.selected_municipality or '').strip()
    if not area_name:
        municipality_names = {entry.municipality_name for entry in warnings if entry.municipality_name}
        if len(municipality_names) == 1:
            area_name = next(iter(municipality_names))

    if count == 1:
        entry = warnings[0]
        area_label = entry.municipality_name or entry.sensor_name
        title = f'Warnung: {area_label}'
        body = ICE_WARNING_LABELS[entry.level]
        municipality_name = entry.municipality_name
    else:
        label = area_name or f'{count} Sensoren'
        title = f'Warnung: {label}'
        body = _digest_body_for_warnings(warnings)
        municipality_name = area_name or worst.municipality_name

    return WarningDigest(
        type='digest',
        title=title,
        body=body,
        alert_status=worst.alert_status,
        municipality_name=municipality_name,
        sensor_count=count,
        worst_level=worst.level,
        worst_severity=worst.severity,
        sensors=tuple(warnings),
    )
