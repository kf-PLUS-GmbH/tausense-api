from django.contrib import admin

from core.admin_mixins import TauSenseModelAdmin
from alerts.models import AlertEvent, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(TauSenseModelAdmin):
    list_display = (
        'name',
        'sensor',
        'municipality',
        'threshold_type',
        'operator',
        'threshold_value',
        'active',
    )
    list_filter = ('active', 'threshold_type')
    search_fields = ('name',)


@admin.register(AlertEvent)
class AlertEventAdmin(TauSenseModelAdmin):
    list_display = (
        'rule',
        'sensor',
        'triggered_at',
        'triggered_value',
        'severity',
    )
    list_filter = ('severity',)
    date_hierarchy = 'triggered_at'
