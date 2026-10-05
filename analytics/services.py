from __future__ import annotations

from django.db import transaction
from analytics.merge import merge_usage_days
from analytics.models import UsageAnalyticsInstallation


@transaction.atomic
def ingest_usage_analytics(
    *,
    installation_id,
    schema_version: int,
    updated_at,
    days: dict,
) -> UsageAnalyticsInstallation:
    record, _created = UsageAnalyticsInstallation.objects.select_for_update().get_or_create(
        installation_id=installation_id,
        defaults={
            'schema_version': schema_version,
            'client_updated_at': updated_at,
            'days': days or {},
        },
    )
    if not _created:
        record.schema_version = schema_version
        if updated_at and (
            record.client_updated_at is None or updated_at >= record.client_updated_at
        ):
            record.client_updated_at = updated_at
        record.days = merge_usage_days(record.days, days or {})
        record.save(
            update_fields=['schema_version', 'client_updated_at', 'days'],
        )
    return record
