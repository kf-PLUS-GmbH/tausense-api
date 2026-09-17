import json
from typing import Any

MAX_LOG_CHARS = 8000


def _key_list(value: Any) -> list[str]:
    if isinstance(value, dict):
        return sorted(str(key) for key in value.keys())
    return []


def summarize_webhook_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {'type': type(data).__name__}

    device_info = data.get('deviceInfo')
    obj = data.get('object')

    summary: dict[str, Any] = {
        'top_level_keys': _key_list(data),
        'has_deviceEui': 'deviceEui' in data or 'devEui' in data,
        'deviceInfo_keys': _key_list(device_info) if isinstance(device_info, dict) else [],
        'object_keys': _key_list(obj) if isinstance(obj, dict) else [],
        'data_field_length': len(data['data']) if isinstance(data.get('data'), str) else None,
    }
    if isinstance(device_info, dict):
        summary['devEui'] = device_info.get('devEui')
        summary['deviceName'] = device_info.get('deviceName')
    if 'deviceEui' in data:
        summary['deviceEui'] = data.get('deviceEui')
    return summary


def format_payload_for_log(data: Any) -> str:
    try:
        text = json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = repr(data)
    if len(text) > MAX_LOG_CHARS:
        return f'{text[:MAX_LOG_CHARS]}… (truncated, {len(text)} chars total)'
    return text
