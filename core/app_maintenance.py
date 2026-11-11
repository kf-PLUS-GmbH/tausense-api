"""Resolve app-wide maintenance banner state for the public API."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from core.models import AppMaintenanceSettings

STATE_INACTIVE = 'inactive'
STATE_SCHEDULED = 'scheduled'
STATE_ACTIVE = 'active'
STATE_ENDED = 'ended'


def resolve_app_maintenance(settings: AppMaintenanceSettings | None = None) -> dict[str, Any]:
    settings = settings or AppMaintenanceSettings.load()
    now = timezone.now()

    if not settings.enabled:
        return _payload(settings, state=STATE_INACTIVE, active=False)

    if settings.starts_at and now < settings.starts_at:
        return _payload(settings, state=STATE_SCHEDULED, active=False)

    if settings.ends_at and now >= settings.ends_at:
        return _payload(settings, state=STATE_ENDED, active=False)

    return _payload(settings, state=STATE_ACTIVE, active=True)


def _payload(
    settings: AppMaintenanceSettings,
    *,
    state: str,
    active: bool,
) -> dict[str, Any]:
    return {
        'active': active,
        'state': state,
        'title': settings.title,
        'message': settings.message,
        'starts_at': settings.starts_at,
        'ends_at': settings.ends_at,
        'updated_at': settings.updated_at,
    }
