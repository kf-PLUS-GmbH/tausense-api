from __future__ import annotations

import re
from datetime import date
from typing import Any

DATE_KEY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DEFAULT_RETAINED_DAYS = 90


def valid_date_key(key: str) -> bool:
    if not DATE_KEY_RE.match(key or ''):
        return False
    try:
        date.fromisoformat(key)
    except ValueError:
        return False
    return True


def merge_usage_days(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
    *,
    retain_days: int = DEFAULT_RETAINED_DAYS,
) -> dict[str, Any]:
    merged = dict(existing or {})
    for day_key, day_in in (incoming or {}).items():
        if not valid_date_key(day_key) or not isinstance(day_in, dict):
            continue
        if day_key not in merged:
            merged[day_key] = day_in
        else:
            merged[day_key] = merge_day(merged[day_key], day_in)
    return trim_old_days(merged, retain_days=retain_days)


def merge_day(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in set(existing) | set(incoming):
        left = existing.get(key)
        right = incoming.get(key)
        if key == 'last_active_at':
            result[key] = max_iso8601(left, right)
        elif key == 'camera_enabled':
            result[key] = right if isinstance(right, bool) else left
        elif isinstance(left, dict) and isinstance(right, dict):
            result[key] = merge_counter_maps(left, right)
        elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
            result[key] = int(left) + int(right)
        elif right is not None:
            result[key] = right
        else:
            result[key] = left
    return result


def merge_counter_maps(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    result = dict(existing)
    for key, right in incoming.items():
        left = result.get(key)
        if isinstance(left, dict) and isinstance(right, dict):
            result[key] = merge_counter_maps(left, right)
        elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
            result[key] = int(left) + int(right)
        elif isinstance(right, (int, float)):
            result[key] = int(right)
        elif isinstance(right, dict):
            base = left if isinstance(left, dict) else {}
            result[key] = merge_counter_maps(base, right)
        elif right is not None:
            result[key] = right
    return result


def max_iso8601(left: Any, right: Any) -> Any:
    left_s = left if isinstance(left, str) else None
    right_s = right if isinstance(right, str) else None
    if not left_s:
        return right_s
    if not right_s:
        return left_s
    return max(left_s, right_s)


def trim_old_days(days: dict[str, Any], *, retain_days: int) -> dict[str, Any]:
    if retain_days <= 0:
        return {}
    keys = sorted(k for k in days if valid_date_key(k))
    if len(keys) <= retain_days:
        return days
    cutoff = date.fromisoformat(keys[-retain_days])
    return {
        key: value
        for key, value in days.items()
        if valid_date_key(key) and date.fromisoformat(key) >= cutoff
    }
