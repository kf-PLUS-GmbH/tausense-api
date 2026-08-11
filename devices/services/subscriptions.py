import logging

from core.ice_warning import (
    ICE_WARNING_LABELS,
    ICE_WARNING_NONE,
    ICE_WARNING_SEVERITY,
    alert_status_for_level,
    evaluate_ice_warning,
)
from core.utils import calculate_dew_point
from devices.models import AlertPreference, PushToken
from devices.services.push import send_push_notification
from readings.models import SensorReading
from sensors.models import Sensor

logger = logging.getLogger(__name__)


def matches_severity_filter(severity_filter: str, alert_status: str) -> bool:
    if severity_filter == AlertPreference.SEVERITY_RED:
        return alert_status == 'red'
    if severity_filter == AlertPreference.SEVERITY_ORANGE:
        return alert_status in ('orange', 'red')
    return False


def matches_subscription(preference: AlertPreference, sensor: Sensor) -> bool:
    """
    Match when the sensor is explicitly selected or falls under the selected area.

    Area matching uses both Sensor.municipality.name and Sensor.operator_name so
    municipality picks in the app work even when only operator_name is populated.
    Favorites and municipality filters are combined with OR logic.
    """
    sensor_ids = preference.selected_sensor_ids or []
    selected_municipality = (preference.selected_municipality or '').strip()
    has_sensor_filter = bool(sensor_ids)
    has_area_filter = bool(selected_municipality)

    if not has_sensor_filter and not has_area_filter:
        return False

    if has_sensor_filter and sensor.id in sensor_ids:
        return True

    if has_area_filter:
        municipality_name = sensor.municipality.name if sensor.municipality else ''
        operator_name = (sensor.operator_name or '').strip()
        if selected_municipality == municipality_name or selected_municipality == operator_name:
            return True

    return False


def find_subscribed_push_tokens(sensor: Sensor, alert_status: str) -> list[PushToken]:
    preferences = AlertPreference.objects.filter(notifications_enabled=True)
    matched_tokens: dict[str, PushToken] = {}

    for preference in preferences:
        if not matches_severity_filter(preference.severity_filter, alert_status):
            continue
        if not matches_subscription(preference, sensor):
            continue
        for token in PushToken.objects.filter(user_id=preference.user_id):
            matched_tokens[token.fcm_token] = token

    return list(matched_tokens.values())


def _ice_warning_level_for_reading(reading: SensorReading) -> str:
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    return evaluate_ice_warning(reading.road_temperature, dew_point, reading.humidity)


def _previous_reading(sensor: Sensor, reading: SensorReading) -> SensorReading | None:
    return (
        SensorReading.objects.filter(sensor=sensor, timestamp__lt=reading.timestamp)
        .order_by('-timestamp')
        .first()
    )


def _should_notify(previous_level: str, new_level: str) -> bool:
    if new_level == ICE_WARNING_NONE:
        return False
    if previous_level == new_level:
        return False
    previous_severity = ICE_WARNING_SEVERITY.get(previous_level, 0)
    new_severity = ICE_WARNING_SEVERITY.get(new_level, 0)
    return new_severity > previous_severity


def notify_sensor_ice_warning(sensor: Sensor, reading: SensorReading, *, force: bool = False) -> dict:
    """
    Evaluate ice warning for a new reading and send push notifications when
    a new warning is created or escalated.
    """
    new_level = _ice_warning_level_for_reading(reading)
    previous = _previous_reading(sensor, reading)
    previous_level = _ice_warning_level_for_reading(previous) if previous else ICE_WARNING_NONE

    if not force and not _should_notify(previous_level, new_level):
        return {
            'notified': False,
            'previous_level': previous_level,
            'new_level': new_level,
            'sent_count': 0,
            'failed_count': 0,
        }

    municipality_name = sensor.municipality.name if sensor.municipality else ''
    sensor_name = sensor.display_name or sensor.name
    alert_status = alert_status_for_level(new_level)
    title = f'Warnung: {sensor_name}'
    body = ICE_WARNING_LABELS[new_level]

    tokens = find_subscribed_push_tokens(sensor, alert_status)
    sent_count = 0
    failed_count = 0

    for token in tokens:
        result = send_push_notification(
            fcm_token=token.fcm_token,
            sensor_id=sensor.id,
            alert_status=alert_status,
            sensor_name=sensor_name,
            municipality_name=municipality_name,
            title=title,
            body=body,
        )
        if result.success:
            sent_count += 1
        else:
            failed_count += 1

    logger.info(
        'Ice warning push for sensor_id=%s (%s -> %s): %s sent, %s failed, %s tokens matched.',
        sensor.id,
        previous_level,
        new_level,
        sent_count,
        failed_count,
        len(tokens),
    )

    return {
        'notified': True,
        'previous_level': previous_level,
        'new_level': new_level,
        'matched_tokens': len(tokens),
        'sent_count': sent_count,
        'failed_count': failed_count,
    }


def send_broadcast_test_pushes(
    *,
    alert_status: str,
    user_id: str | None = None,
    sensor: Sensor | None = None,
) -> dict:
    """
    Send a test push to registered tokens, bypassing preference filters.
    Useful for manual push testing including green/yellow statuses.
    """
    from core.ice_warning import (
        ICE_WARNING_ACUTE_ICE,
        ICE_WARNING_INCREASED_ICE,
        ICE_WARNING_LABELS,
        ICE_WARNING_NONE,
        ICE_WARNING_POSSIBLE_SLIP,
    )

    status_labels = {
        'green': ICE_WARNING_LABELS[ICE_WARNING_NONE],
        'yellow': ICE_WARNING_LABELS[ICE_WARNING_POSSIBLE_SLIP],
        'orange': ICE_WARNING_LABELS[ICE_WARNING_INCREASED_ICE],
        'red': ICE_WARNING_LABELS[ICE_WARNING_ACUTE_ICE],
    }
    body = status_labels.get(alert_status, f'Test-{alert_status}')

    tokens = list(PushToken.objects.all())
    if user_id:
        tokens = [token for token in tokens if token.user_id == user_id]

    if sensor is None:
        sensor = Sensor.objects.filter(active=True).first()

    sensor_id = sensor.id if sensor else 0
    sensor_name = (sensor.display_name or sensor.name) if sensor else 'Test Sensor'
    municipality_name = sensor.municipality.name if sensor and sensor.municipality else 'Hof'
    title = f'Test Warnung: {sensor_name}'

    sent_count = 0
    failed_count = 0
    for token in tokens:
        result = send_push_notification(
            fcm_token=token.fcm_token,
            sensor_id=sensor_id,
            alert_status=alert_status,
            sensor_name=sensor_name,
            municipality_name=municipality_name,
            title=title,
            body=body,
        )
        if result.success:
            sent_count += 1
        else:
            failed_count += 1

    return {
        'alert_status': alert_status,
        'matched_tokens': len(tokens),
        'sent_count': sent_count,
        'failed_count': failed_count,
    }
