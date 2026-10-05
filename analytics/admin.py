from django.contrib import admin

from analytics.models import UsageAnalyticsInstallation
from core.admin_mixins import TauSenseModelAdmin


@admin.register(UsageAnalyticsInstallation)
class UsageAnalyticsInstallationAdmin(TauSenseModelAdmin):
    list_display = (
        'installation_id',
        'schema_version',
        'day_count_display',
        'client_updated_at',
        'last_upload_at',
        'first_seen_at',
    )
    search_fields = ('installation_id',)
    readonly_fields = (
        'installation_id',
        'schema_version',
        'client_updated_at',
        'days',
        'first_seen_at',
        'last_upload_at',
    )

    @admin.display(description='Days stored')
    def day_count_display(self, obj: UsageAnalyticsInstallation) -> int:
        return obj.day_count

    def has_add_permission(self, request):
        return False
