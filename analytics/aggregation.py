from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from django.utils import timezone

from analytics.merge import valid_date_key

SCREEN_LABELS = {
    'map': 'Karte',
    'dashboard': 'Dashboard',
    'settings': 'Einstellungen',
}

ACTION_LABELS = {
    'location_button': 'Standort-Button',
    'camera_switch_on': 'Kamera eingeschaltet',
    'camera_switch_off': 'Kamera ausgeschaltet',
}

CONNECTIVITY_LABELS = {
    'wifi': 'WLAN',
    'mobile': 'Mobilfunk',
    'offline': 'Offline',
    'other': 'Sonstiges',
}


def period_days_from_request(value: str | None) -> int:
    if value in {'7', '30', '90'}:
        return int(value)
    return 30


def _label(mapping: dict[str, str], key: str) -> str:
    return mapping.get(key, key.replace('_', ' ').replace(':', ' · ').title())


def _merge_counters(target: dict[str, int], source: dict[str, Any] | None) -> None:
    if not isinstance(source, dict):
        return
    for key, value in source.items():
        if isinstance(value, dict):
            nested = target.setdefault(f'__nested__{key}', {})
            if not isinstance(nested, dict):
                nested = {}
                target[f'__nested__{key}'] = nested
            _merge_flat_counters(nested, value)
        elif isinstance(value, (int, float)):
            target[str(key)] = target.get(str(key), 0) + int(value)


def _merge_flat_counters(target: dict[str, int], source: dict[str, Any] | None) -> None:
    if not isinstance(source, dict):
        return
    for key, value in source.items():
        if isinstance(value, (int, float)):
            key_s = str(key)
            target[key_s] = target.get(key_s, 0) + int(value)


def _top_items(counter: dict[str, int], *, limit: int = 8) -> list[tuple[str, int]]:
    items = [(key, count) for key, count in counter.items() if not key.startswith('__nested__')]
    items.sort(key=lambda item: (-item[1], item[0]))
    return items[:limit]


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(100.0 * part / whole, 1)


@dataclass
class DaySeriesPoint:
    date_key: str
    label: str
    sessions: int
    active_installations: int


@dataclass
class RankedMetric:
    key: str
    label: str
    count: int
    share_pct: float


@dataclass
class InstallationReport:
    installation_id: str
    period_days: int
    period_start: date
    period_end: date
    total_sessions: int
    active_days: int
    last_active_at: str | None
    sessions_series: list[DaySeriesPoint] = field(default_factory=list)
    screens: list[RankedMetric] = field(default_factory=list)
    actions: list[RankedMetric] = field(default_factory=list)
    municipalities: list[RankedMetric] = field(default_factory=list)
    sensors: list[RankedMetric] = field(default_factory=list)
    status_filters: list[RankedMetric] = field(default_factory=list)
    connectivity_sessions: list[RankedMetric] = field(default_factory=list)
    connectivity: list[RankedMetric] = field(default_factory=list)
    camera_enabled_days: int = 0


@dataclass
class DashboardReport:
    period_days: int
    period_start: date
    period_end: date
    installation_count: int
    active_installations: int
    total_sessions: int
    avg_sessions_per_active: float
    last_upload_at: datetime | None
    sessions_series: list[DaySeriesPoint] = field(default_factory=list)
    max_sessions_in_day: int = 0
    screens: list[RankedMetric] = field(default_factory=list)
    actions: list[RankedMetric] = field(default_factory=list)
    municipalities: list[RankedMetric] = field(default_factory=list)
    sensors: list[RankedMetric] = field(default_factory=list)
    status_filters: list[RankedMetric] = field(default_factory=list)
    connectivity_sessions: list[RankedMetric] = field(default_factory=list)
    connectivity: list[RankedMetric] = field(default_factory=list)
    camera_enabled_days: int = 0
    recent_installations: list[dict[str, Any]] = field(default_factory=list)


def _period_bounds(period_days: int) -> tuple[date, date]:
    end = timezone.localdate()
    start = end - timedelta(days=period_days - 1)
    return start, end


def _day_in_period(day_key: str, start: date, end: date) -> bool:
    if not valid_date_key(day_key):
        return False
    day = date.fromisoformat(day_key)
    return start <= day <= end


def _format_day_label(day_key: str) -> str:
    day = date.fromisoformat(day_key)
    return day.strftime('%d.%m.')


def _extract_day_counters(day: dict[str, Any]) -> dict[str, dict[str, int]]:
    screens: dict[str, int] = {}
    actions: dict[str, int] = {}
    municipalities: dict[str, int] = {}
    sensors: dict[str, int] = {}
    status_filters: dict[str, int] = {}
    connectivity_sessions: dict[str, int] = {}
    connectivity: dict[str, int] = {}

    _merge_flat_counters(screens, day.get('screens'))
    _merge_flat_counters(actions, day.get('actions'))
    filters = day.get('filters') if isinstance(day.get('filters'), dict) else {}
    for key, value in filters.items():
        if key == 'municipalities' and isinstance(value, dict):
            _merge_flat_counters(municipalities, value)
        elif key == 'sensor_ids' and isinstance(value, dict):
            _merge_flat_counters(sensors, value)
        elif isinstance(value, (int, float)):
            status_filters[str(key)] = status_filters.get(str(key), 0) + int(value)
    _merge_flat_counters(connectivity_sessions, day.get('connectivity_sessions'))
    _merge_flat_counters(connectivity, day.get('connectivity'))

    return {
        'screens': screens,
        'actions': actions,
        'municipalities': municipalities,
        'sensors': sensors,
        'status_filters': status_filters,
        'connectivity_sessions': connectivity_sessions,
        'connectivity': connectivity,
    }


def _to_ranked(
    counter: dict[str, int],
    *,
    label_fn,
    total: int | None = None,
    limit: int = 8,
) -> list[RankedMetric]:
    if total is None:
        total = sum(counter.values())
    ranked = []
    for key, count in _top_items(counter, limit=limit):
        ranked.append(
            RankedMetric(
                key=key,
                label=label_fn(key),
                count=count,
                share_pct=_pct(count, total),
            ),
        )
    return ranked


def build_installation_report(days_payload: dict[str, Any], *, period_days: int) -> InstallationReport:
    start, end = _period_bounds(period_days)
    totals = {
        'screens': {},
        'actions': {},
        'municipalities': {},
        'sensors': {},
        'status_filters': {},
        'connectivity_sessions': {},
        'connectivity': {},
    }
    series_map: dict[str, DaySeriesPoint] = {}
    total_sessions = 0
    active_days = 0
    last_active_at: str | None = None
    camera_enabled_days = 0

    for day_key, day in (days_payload or {}).items():
        if not _day_in_period(day_key, start, end) or not isinstance(day, dict):
            continue
        active_days += 1
        sessions = int(day.get('sessions') or 0)
        total_sessions += sessions
        if day.get('camera_enabled') is True:
            camera_enabled_days += 1
        day_last = day.get('last_active_at')
        if isinstance(day_last, str) and (last_active_at is None or day_last > last_active_at):
            last_active_at = day_last

        counters = _extract_day_counters(day)
        for bucket, values in counters.items():
            _merge_flat_counters(totals[bucket], values)

        series_map[day_key] = DaySeriesPoint(
            date_key=day_key,
            label=_format_day_label(day_key),
            sessions=sessions,
            active_installations=1 if sessions > 0 else 0,
        )

    series = sorted(series_map.values(), key=lambda point: point.date_key)

    return InstallationReport(
        installation_id='',
        period_days=period_days,
        period_start=start,
        period_end=end,
        total_sessions=total_sessions,
        active_days=active_days,
        last_active_at=last_active_at,
        sessions_series=series,
        screens=_to_ranked(totals['screens'], label_fn=lambda k: _label(SCREEN_LABELS, k)),
        actions=_to_ranked(totals['actions'], label_fn=lambda k: _label(ACTION_LABELS, k)),
        municipalities=_to_ranked(
            totals['municipalities'],
            label_fn=lambda k: k if k != 'all' else 'Alle Gemeinden',
        ),
        sensors=_to_ranked(
            totals['sensors'],
            label_fn=lambda k: f'Sensor #{k}',
        ),
        status_filters=_to_ranked(
            totals['status_filters'],
            label_fn=lambda k: k.replace('status:', 'Status · '),
        ),
        connectivity_sessions=_to_ranked(
            totals['connectivity_sessions'],
            label_fn=lambda k: _label(CONNECTIVITY_LABELS, k),
        ),
        connectivity=_to_ranked(
            totals['connectivity'],
            label_fn=lambda k: _label(CONNECTIVITY_LABELS, k),
        ),
        camera_enabled_days=camera_enabled_days,
    )


def build_dashboard(installations, *, period_days: int) -> DashboardReport:
    start, end = _period_bounds(period_days)
    totals = {
        'screens': {},
        'actions': {},
        'municipalities': {},
        'sensors': {},
        'status_filters': {},
        'connectivity_sessions': {},
        'connectivity': {},
    }
    series_sessions: dict[str, int] = {}
    series_active: dict[str, int] = {}
    total_sessions = 0
    active_installations = 0
    last_upload_at = None
    camera_enabled_days = 0

    for record in installations:
        if last_upload_at is None or record.last_upload_at > last_upload_at:
            last_upload_at = record.last_upload_at

        had_activity = False
        for day_key, day in (record.days or {}).items():
            if not _day_in_period(day_key, start, end) or not isinstance(day, dict):
                continue
            sessions = int(day.get('sessions') or 0)
            if sessions > 0:
                had_activity = True
            total_sessions += sessions
            series_sessions[day_key] = series_sessions.get(day_key, 0) + sessions
            if sessions > 0:
                series_active[day_key] = series_active.get(day_key, 0) + 1
            if day.get('camera_enabled') is True:
                camera_enabled_days += 1
            counters = _extract_day_counters(day)
            for bucket, values in counters.items():
                _merge_flat_counters(totals[bucket], values)

        if had_activity:
            active_installations += 1

    series: list[DaySeriesPoint] = []
    max_sessions = 0
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        sessions = series_sessions.get(key, 0)
        max_sessions = max(max_sessions, sessions)
        series.append(
            DaySeriesPoint(
                date_key=key,
                label=cursor.strftime('%d.%m.'),
                sessions=sessions,
                active_installations=series_active.get(key, 0),
            ),
        )
        cursor += timedelta(days=1)

    installation_count = installations.count() if hasattr(installations, 'count') else len(installations)
    avg_sessions = (
        round(total_sessions / active_installations, 1) if active_installations else 0.0
    )

    recent = []
    for record in installations.order_by('-last_upload_at')[:6]:
        recent.append(
            {
                'id': record.pk,
                'installation_id': str(record.installation_id),
                'short_id': str(record.installation_id)[:8],
                'last_upload_at': record.last_upload_at,
                'day_count': record.day_count,
            },
        )

    return DashboardReport(
        period_days=period_days,
        period_start=start,
        period_end=end,
        installation_count=installation_count,
        active_installations=active_installations,
        total_sessions=total_sessions,
        avg_sessions_per_active=avg_sessions,
        last_upload_at=last_upload_at,
        sessions_series=series,
        max_sessions_in_day=max_sessions or 1,
        screens=_to_ranked(totals['screens'], label_fn=lambda k: _label(SCREEN_LABELS, k)),
        actions=_to_ranked(totals['actions'], label_fn=lambda k: _label(ACTION_LABELS, k)),
        municipalities=_to_ranked(
            totals['municipalities'],
            label_fn=lambda k: k if k != 'all' else 'Alle Gemeinden',
            limit=10,
        ),
        sensors=_to_ranked(
            totals['sensors'],
            label_fn=lambda k: f'Sensor #{k}',
            limit=10,
        ),
        status_filters=_to_ranked(
            totals['status_filters'],
            label_fn=lambda k: k.replace('status:', 'Status · '),
        ),
        connectivity_sessions=_to_ranked(
            totals['connectivity_sessions'],
            label_fn=lambda k: _label(CONNECTIVITY_LABELS, k),
        ),
        connectivity=_to_ranked(
            totals['connectivity'],
            label_fn=lambda k: _label(CONNECTIVITY_LABELS, k),
        ),
        camera_enabled_days=camera_enabled_days,
        recent_installations=recent,
    )
