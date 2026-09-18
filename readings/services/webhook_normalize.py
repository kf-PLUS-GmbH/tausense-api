from typing import Any

from sensors.services.coordinates import coordinates_from_device_name

# Decoded payload keys from some codecs / middleware → our flat ingest format.
FIELD_ALIASES = {
    'road_temperature': 'surface_temperature',
    'RoadTemperature': 'surface_temperature',
    'surfaceTemperature': 'surface_temperature',
    'airTemperatureRadiationShield': 'air_temperature_radiation_shield',
    'airHumidityRadiationShield': 'air_humidity_radiation_shield',
    'airTemperature': 'air_temperature',
    'airHumidity': 'air_humidity',
    'dewPoint': 'dew_point',
    'deviceEUI': 'deviceEui',
    'dev_eui': 'deviceEui',
}


def should_ignore_webhook_event(event: str | None) -> bool:
    if not event:
        return False
    return event.strip().lower() != 'up'


def _apply_aliases(payload: dict[str, Any]) -> None:
    for source, target in FIELD_ALIASES.items():
        if source in payload and target not in payload:
            payload[target] = payload[source]


def normalize_incoming_webhook_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten ChirpStack HTTP integration payloads (and similar) into the format
    expected by LorawanWebhookPayloadSerializer / ingest_lorawan_payload.
    """
    payload = dict(data)

    device_info = payload.pop('deviceInfo', None) or {}
    if not isinstance(device_info, dict):
        device_info = {}

    obj = payload.pop('object', None)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if value is not None:
                payload[key] = value

    if not payload.get('deviceEui'):
        dev_eui = device_info.get('devEui') or payload.get('devEui')
        if dev_eui:
            payload['deviceEui'] = dev_eui

    if not payload.get('deviceName'):
        device_name = device_info.get('deviceName')
        if device_name:
            payload['deviceName'] = device_name

    if not payload.get('timestamp') and payload.get('time'):
        payload['timestamp'] = payload['time']

    rx_info = payload.get('rxInfo')
    if isinstance(rx_info, list) and rx_info:
        first_rx = rx_info[0] if isinstance(rx_info[0], dict) else {}
        if not payload.get('timestamp') and not payload.get('rxTime'):
            gw_time = first_rx.get('gwTime') or first_rx.get('nsTime')
            if gw_time:
                payload['rxTime'] = gw_time
        # Do not use rxInfo.location for lat/lon — that is often the gateway, not the sensor.

    device_name = payload.get('deviceName') or ''
    name_coords = coordinates_from_device_name(str(device_name))
    if name_coords:
        payload['lat'] = float(name_coords[0])
        payload['lon'] = float(name_coords[1])
    elif payload.get('lat') is None and payload.get('lon') is None:
        sensor_name = payload.get('device_name') or ''
        fallback = coordinates_from_device_name(str(sensor_name))
        if fallback:
            payload['lat'] = float(fallback[0])
            payload['lon'] = float(fallback[1])

    _apply_aliases(payload)
    return payload
