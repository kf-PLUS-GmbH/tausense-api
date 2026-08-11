import logging
from dataclasses import dataclass

from devices.firebase_app import is_firebase_ready

logger = logging.getLogger(__name__)


@dataclass
class PushNotificationPayload:
    sensor_id: int
    alert_status: str
    sensor_name: str
    municipality_name: str
    title: str
    body: str


@dataclass
class PushSendResult:
    success: bool
    fcm_token: str
    message_id: str | None = None
    error: str | None = None
    token_removed: bool = False


def send_push_notification(
    *,
    fcm_token: str,
    sensor_id: int,
    alert_status: str,
    sensor_name: str,
    municipality_name: str,
    title: str,
    body: str,
) -> PushSendResult:
    """
    Send a Firebase Cloud Message with a data payload to one device token.
    """
    payload = PushNotificationPayload(
        sensor_id=sensor_id,
        alert_status=alert_status,
        sensor_name=sensor_name,
        municipality_name=municipality_name,
        title=title,
        body=body,
    )
    return _send_to_token(fcm_token, payload)


def _send_to_token(fcm_token: str, payload: PushNotificationPayload) -> PushSendResult:
    if not is_firebase_ready():
        error = 'Firebase is not initialized.'
        logger.error('Push skipped for token %s: %s', _token_preview(fcm_token), error)
        return PushSendResult(success=False, fcm_token=fcm_token, error=error)

    from firebase_admin import exceptions, messaging

    message = messaging.Message(
        token=fcm_token,
        notification=messaging.Notification(
            title=payload.title,
            body=payload.body,
        ),
        data={
            'sensor_id': str(payload.sensor_id),
            'alert_status': payload.alert_status,
            'sensor_name': payload.sensor_name,
            'municipality_name': payload.municipality_name,
            'title': payload.title,
            'body': payload.body,
        },
    )

    try:
        message_id = messaging.send(message)
        logger.info(
            'Push sent successfully to %s (sensor_id=%s, alert_status=%s, message_id=%s).',
            _token_preview(fcm_token),
            payload.sensor_id,
            payload.alert_status,
            message_id,
        )
        return PushSendResult(
            success=True,
            fcm_token=fcm_token,
            message_id=message_id,
        )
    except messaging.UnregisteredError:
        logger.warning('Invalid FCM token removed: %s', _token_preview(fcm_token))
        _remove_invalid_token(fcm_token)
        return PushSendResult(
            success=False,
            fcm_token=fcm_token,
            error='Unregistered FCM token.',
            token_removed=True,
        )
    except messaging.SenderIdMismatchError:
        logger.warning('Sender ID mismatch for token %s', _token_preview(fcm_token))
        _remove_invalid_token(fcm_token)
        return PushSendResult(
            success=False,
            fcm_token=fcm_token,
            error='Sender ID mismatch.',
            token_removed=True,
        )
    except exceptions.FirebaseError as exc:
        logger.error(
            'Firebase error while sending push to %s: %s',
            _token_preview(fcm_token),
            exc,
        )
        return PushSendResult(
            success=False,
            fcm_token=fcm_token,
            error=str(exc),
        )
    except Exception as exc:
        logger.exception(
            'Unexpected error while sending push to %s',
            _token_preview(fcm_token),
        )
        return PushSendResult(
            success=False,
            fcm_token=fcm_token,
            error=str(exc),
        )


def _remove_invalid_token(fcm_token: str) -> None:
    from devices.models import PushToken

    PushToken.objects.filter(fcm_token=fcm_token).delete()


def _token_preview(fcm_token: str) -> str:
    if len(fcm_token) <= 12:
        return fcm_token
    return f'{fcm_token[:8]}...{fcm_token[-4:]}'
