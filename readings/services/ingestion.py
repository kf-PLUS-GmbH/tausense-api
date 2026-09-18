from datetime import datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from readings.models import SensorReading
from sensors.models import Sensor
from sensors.services.coordinates import coordinates_from_device_name
from sensors.services.device_matching import find_sensor_by_webhook_device_name


class WebhookIngestionError(Exception):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


def _parse_timestamp(payload: dict[str, Any]) -> datetime:
    raw = payload.get('timestamp') or payload.get('rxTime')
    if not raw:
        raise WebhookIngestionError('timestamp or rxTime is required', field='timestamp')

    if isinstance(raw, datetime):
        value = raw
    else:
        text = str(raw).replace('Z', '+00:00')
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise WebhookIngestionError('Invalid timestamp format', field='timestamp') from exc

    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.utc)
    return value


def _pick_float(payload: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return float(value)
    raise WebhookIngestionError(
        f'One of {", ".join(keys)} is required',
        field=keys[0],
    )


def _optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    return float(value)


def _optional_decimal(payload: dict[str, Any], key: str) -> Decimal | None:
    value = payload.get(key)
    if value is None:
        return None
    return Decimal(str(value))


def _resolve_sensor(payload: dict[str, Any]) -> Sensor:
    device_eui = payload.get('deviceEui')
    if not device_eui:
        raise WebhookIngestionError('deviceEui is required', field='deviceEui')

    external_id = str(device_eui).strip().upper()
    device_name = str(payload.get('deviceName') or '').strip()
    sensor = Sensor.objects.filter(external_id=external_id).first()
    if not sensor and device_name:
        sensor = find_sensor_by_webhook_device_name(device_name)
        if sensor:
            sensor.external_id = external_id
            sensor.save(update_fields=['external_id'])
    if sensor:
        return _maybe_update_sensor_coordinates(sensor, payload)

    if not getattr(settings, 'WEBHOOK_AUTO_CREATE_SENSOR', True):
        raise WebhookIngestionError(
            f'Unknown sensor {external_id}',
            field='deviceEui',
        )

    lat = payload.get('lat')
    lon = payload.get('lon')
    if lat is None or lon is None:
        raise WebhookIngestionError(
            'lat and lon are required for new sensors',
            field='lat',
        )

    name = device_name or external_id
    return Sensor.objects.create(
        external_id=external_id,
        name=name,
        device_name=device_name or None,
        municipality=None,
        latitude=Decimal(str(lat)),
        longitude=Decimal(str(lon)),
        sensor_type=Sensor.TYPE_STANDARD,
        active=True,
    )


def _maybe_update_sensor_coordinates(sensor: Sensor, payload: dict[str, Any]) -> Sensor:
    updates = {}
    install_coords = coordinates_from_device_name(
        sensor.device_name or str(payload.get('deviceName') or '')
    )
    if install_coords:
        new_lat, new_lon = install_coords
        if sensor.latitude != new_lat:
            updates['latitude'] = new_lat
        if sensor.longitude != new_lon:
            updates['longitude'] = new_lon
    else:
        lat = payload.get('lat')
        lon = payload.get('lon')
        if lat is not None and lon is not None and (
            sensor.latitude is None or sensor.longitude is None
        ):
            new_lat = Decimal(str(lat))
            new_lon = Decimal(str(lon))
            if sensor.latitude != new_lat:
                updates['latitude'] = new_lat
            if sensor.longitude != new_lon:
                updates['longitude'] = new_lon
    device_name = payload.get('deviceName')
    if device_name and sensor.device_name != device_name:
        updates['device_name'] = device_name
    if device_name and not sensor.display_name and sensor.name != device_name:
        updates['name'] = device_name
    if updates:
        for field, value in updates.items():
            setattr(sensor, field, value)
        sensor.save(update_fields=list(updates.keys()))
    return sensor


@transaction.atomic
def ingest_lorawan_payload(
    payload: dict[str, Any],
    *,
    raw_payload: dict[str, Any] | None = None,
) -> SensorReading:
    sensor = _resolve_sensor(payload)
    timestamp = _parse_timestamp(payload)
    air_temperature = _pick_float(
        payload,
        'air_temperature_radiation_shield',
        'air_temperature',
    )
    humidity = _pick_float(
        payload,
        'air_humidity_radiation_shield',
        'air_humidity',
    )
    road_temperature = _pick_float(payload, 'surface_temperature')

    reading, _ = SensorReading.objects.update_or_create(
        sensor=sensor,
        timestamp=timestamp,
        defaults={
            'device_name': payload.get('deviceName') or '',
            'air_temperature': air_temperature,
            'road_temperature': road_temperature,
            'humidity': humidity,
            'air_temperature_radiation_shield': _optional_float(
                payload,
                'air_temperature_radiation_shield',
            ),
            'air_humidity_radiation_shield': _optional_float(
                payload,
                'air_humidity_radiation_shield',
            ),
            'air_temperature_unshielded': _optional_float(payload, 'air_temperature'),
            'air_humidity_unshielded': _optional_float(payload, 'air_humidity'),
            'reported_dew_point': _optional_float(payload, 'dew_point'),
            'angle': _optional_float(payload, 'angle'),
            'sensor_temperature': _optional_float(payload, 'sensor_temperature'),
            'battery_voltage': _optional_float(payload, 'battery_voltage'),
            'latitude': _optional_decimal(payload, 'lat'),
            'longitude': _optional_decimal(payload, 'lon'),
            'raw_data': raw_payload if raw_payload is not None else payload,
        },
    )

    from devices.services.subscriptions import notify_sensor_ice_warning

    notify_sensor_ice_warning(sensor, reading)
    return reading


def ingest_lorawan_payloads(payloads: list[dict[str, Any]]) -> list[SensorReading]:
    return [ingest_lorawan_payload(item) for item in payloads]
