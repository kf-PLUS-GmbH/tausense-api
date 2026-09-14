import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.ice_warning import (
    ICE_WARNING_NONE,
    alert_status_for_level,
    evaluate_ice_warning,
)
from core.utils import calculate_dew_point
from devices.models import AlertPreference, PushDigestState, PushNotificationState, PushToken
from devices.services.digest import build_warning_digest, collect_warning_sensors
from devices.services.push import send_digest_push_notification
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


def find_subscribed_preferences(
    sensor: Sensor,
    alert_status: str,
) -> list[tuple[AlertPreference, list[PushToken]]]:
    preferences = AlertPreference.objects.filter(notifications_enabled=True)
    matched: list[tuple[AlertPreference, list[PushToken]]] = []

    for preference in preferences:
        if not matches_severity_filter(preference.severity_filter, alert_status):
            continue
        if not matches_subscription(preference, sensor):
            continue
        tokens = list(PushToken.objects.filter(user_id=preference.user_id))
        if tokens:
            matched.append((preference, tokens))

    return matched


def find_subscribed_push_tokens(sensor: Sensor, alert_status: str) -> list[PushToken]:
    matched_tokens: dict[str, PushToken] = {}

    for _preference, tokens in find_subscribed_preferences(sensor, alert_status):
        for token in tokens:
            matched_tokens[token.fcm_token] = token

    return list(matched_tokens.values())


def _ice_warning_level_for_reading(reading: SensorReading) -> str:
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    return evaluate_ice_warning(reading.road_temperature, dew_point, reading.humidity)


def _reminder_interval() -> timedelta:
    minutes = getattr(settings, 'PUSH_REMINDER_MINUTES', 30)
    return timedelta(minutes=minutes)


def _should_send_digest(
    *,
    state: PushDigestState | None,
    worst_severity: int,
    sensor_count: int,
    force: bool = False,
) -> bool:
    if force:
        return True
    if sensor_count == 0:
        return False
    if state is None:
        return True
    if worst_severity > state.last_worst_severity:
        return True
    if sensor_count > state.last_sensor_count:
        return True
    elapsed = timezone.now() - state.last_sent_at
    return elapsed >= _reminder_interval()


def _record_digest_state(user_id: str, *, worst_severity: int, sensor_count: int) -> None:
    PushDigestState.objects.update_or_create(
        user_id=user_id,
        defaults={
            'last_worst_severity': worst_severity,
            'last_sensor_count': sensor_count,
            'last_sent_at': timezone.now(),
        },
    )


def _reset_digest_state_if_cleared(preference: AlertPreference) -> None:
    if not collect_warning_sensors(preference):
        PushDigestState.objects.filter(user_id=preference.user_id).delete()


def _preferences_for_sensor(sensor: Sensor) -> list[AlertPreference]:
    preferences = AlertPreference.objects.filter(notifications_enabled=True)
    return [preference for preference in preferences if matches_subscription(preference, sensor)]


def notify_sensor_ice_warning(sensor: Sensor, reading: SensorReading, *, force: bool = False) -> dict:
    """
    Evaluate ice warning for a new reading and send grouped digest push notifications.
    """
    new_level = _ice_warning_level_for_reading(reading)

    if new_level == ICE_WARNING_NONE:
        PushNotificationState.objects.filter(sensor=sensor).delete()
        for preference in _preferences_for_sensor(sensor):
            _reset_digest_state_if_cleared(preference)
        return {
            'notified': False,
            'new_level': new_level,
            'sent_count': 0,
            'failed_count': 0,
        }

    alert_status = alert_status_for_level(new_level)
    candidates = find_subscribed_preferences(sensor, alert_status)

    sent_count = 0
    failed_count = 0
    notified_users = 0
    processed_users: set[str] = set()

    for preference, tokens in candidates:
        if preference.user_id in processed_users:
            continue
        processed_users.add(preference.user_id)

        warnings = collect_warning_sensors(preference)
        digest = build_warning_digest(preference, warnings)
        if digest is None:
            continue

        state = PushDigestState.objects.filter(user_id=preference.user_id).first()
        if not _should_send_digest(
            state=state,
            worst_severity=digest.worst_severity,
            sensor_count=digest.sensor_count,
            force=force,
        ):
            continue

        notified_users += 1
        for token in tokens:
            result = send_digest_push_notification(fcm_token=token.fcm_token, digest=digest)
            if result.success:
                sent_count += 1
            else:
                failed_count += 1

        _record_digest_state(
            preference.user_id,
            worst_severity=digest.worst_severity,
            sensor_count=digest.sensor_count,
        )

    logger.info(
        'Ice warning digest for sensor_id=%s (%s): %s users notified, %s sent, %s failed.',
        sensor.id,
        new_level,
        notified_users,
        sent_count,
        failed_count,
    )

    return {
        'notified': notified_users > 0,
        'new_level': new_level,
        'matched_users': notified_users,
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
    from devices.services.push import send_push_notification

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
