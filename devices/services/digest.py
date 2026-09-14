from dataclasses import dataclass

from django.db.models import Q

from core.ice_warning import ICE_WARNING_LABELS, ICE_WARNING_NONE, ICE_WARNING_SEVERITY, alert_status_for_level, evaluate_ice_warning
from core.utils import calculate_dew_point
from devices.models import AlertPreference
from readings.selectors import latest_readings_queryset
from sensors.models import Sensor


def _ice_warning_level_for_reading(reading) -> str:
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    return evaluate_ice_warning(reading.road_temperature, dew_point, reading.humidity)


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
    latest_readings = latest_readings_queryset().filter(sensor_id__in=subscribed_ids)

    for reading in latest_readings:
        level = _ice_warning_level_for_reading(reading)
        if level == ICE_WARNING_NONE:
            continue

        alert_status = alert_status_for_level(level)
        if not _matches_severity_filter(preference.severity_filter, alert_status):
            continue

        sensor = reading.sensor
        municipality_name = sensor.municipality.name if sensor.municipality else (sensor.operator_name or '')
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
        title = f'Warnung: {entry.sensor_name}'
        body = ICE_WARNING_LABELS[entry.level]
        municipality_name = entry.municipality_name
    else:
        label = area_name or f'{count} Sensoren'
        title = f'Warnung: {label}'
        body = f'{ICE_WARNING_LABELS[worst.level]} an {count} Standorten'
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
