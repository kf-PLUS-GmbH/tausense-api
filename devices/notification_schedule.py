"""
Per-user quiet hours for push digests (IANA timezone, local wall clock).

Contract (app): notification_schedule = {
  "enabled": bool,
  "start": "HH:MM",
  "end": "HH:MM",
  "timezone": "Europe/Berlin",
}
When enabled is false, pushes are always allowed. When enabled is true:
- start == end means allow notifications all day.
- Otherwise the window is inclusive on local calendar minutes (e.g. 03:00–22:00).
- If start > end on the clock, the window spans midnight (e.g. 22:00–06:00).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from django.utils import timezone as django_timezone

_HHMM_RE = re.compile(r'^(?P<h>\d{2}):(?P<m>\d{2})$')


def default_notification_schedule() -> dict[str, Any]:
    return {
        'enabled': False,
        'start': '03:00',
        'end': '22:00',
        'timezone': 'Europe/Berlin',
    }


def parse_hhmm_minutes(value: str) -> int:
    m = _HHMM_RE.match(value.strip())
    if not m:
        raise ValueError('expected HH:MM')
    h, mm = int(m['h']), int(m['m'])
    if not (0 <= h <= 23 and 0 <= mm <= 59):
        raise ValueError('invalid hour or minute')
    return h * 60 + mm


def local_minutes_now(tz_name: str) -> int:
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now = django_timezone.now()
    if now.tzinfo is None:
        now = django_timezone.make_aware(now, django_timezone.get_current_timezone())
    local: datetime = now.astimezone(tz)
    return local.hour * 60 + local.minute


def is_within_notification_window(
    *,
    start: str,
    end: str,
    tz_name: str,
    now_minutes: int | None = None,
) -> bool:
    """Return True if current local time (in tz_name) lies in [start, end] rules."""
    start_m = parse_hhmm_minutes(start)
    end_m = parse_hhmm_minutes(end)
    if now_minutes is None:
        now_minutes = local_minutes_now(tz_name)
    if start_m == end_m:
        return True
    if start_m < end_m:
        return start_m <= now_minutes <= end_m
    # Overnight: e.g. 22:00–06:00
    return now_minutes >= start_m or now_minutes <= end_m


def normalize_notification_schedule(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Merge with defaults and coerce types."""
    base = default_notification_schedule()
    if not raw:
        return base
    out = {**base, **raw}
    out['enabled'] = bool(out.get('enabled', False))
    out['start'] = str(out.get('start', base['start']))
    out['end'] = str(out.get('end', base['end']))
    out['timezone'] = str(out.get('timezone', base['timezone'])).strip() or base['timezone']
    return out


def is_push_allowed_by_schedule(
    schedule: dict[str, Any] | None,
    *,
    now_minutes: int | None = None,
) -> bool:
    if not schedule or not schedule.get('enabled'):
        return True
    sch = normalize_notification_schedule(schedule)
    try:
        return is_within_notification_window(
            start=sch['start'],
            end=sch['end'],
            tz_name=sch['timezone'],
            now_minutes=now_minutes,
        )
    except (ValueError, KeyError, OSError):
        # Bad tz or bad times — fail open so users still get safety alerts
        return True
