from django.contrib import admin

from core.admin_mixins import TauSenseModelAdmin
from devices.models import (
    AlertPreference,
    PushDigestState,
    PushNotificationState,
    PushToken,
)


@admin.register(AlertPreference)
class AlertPreferenceAdmin(TauSenseModelAdmin):
    list_display = (
        'user_id',
        'severity_filter',
        'notifications_enabled',
        'selected_municipality',
        'updated_at',
    )
    search_fields = ('user_id', 'selected_municipality')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PushToken)
class PushTokenAdmin(TauSenseModelAdmin):
    list_display = (
        'id',
        'user_id',
        'platform',
        'updated_at',
    )
    search_fields = ('user_id', 'fcm_token')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PushNotificationState)
class PushNotificationStateAdmin(TauSenseModelAdmin):
    list_display = ('user_id', 'sensor', 'last_level', 'last_sent_at', 'updated_at')
    list_filter = ('last_level',)
    search_fields = ('user_id',)
    readonly_fields = ('updated_at',)


@admin.register(PushDigestState)
class PushDigestStateAdmin(TauSenseModelAdmin):
    list_display = (
        'user_id',
        'last_worst_severity',
        'last_sensor_count',
        'last_sent_at',
        'updated_at',
    )
    search_fields = ('user_id',)
    readonly_fields = ('updated_at',)
