from django.contrib import admin

from devices.models import AlertPreference, PushToken


@admin.register(AlertPreference)
class AlertPreferenceAdmin(admin.ModelAdmin):
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
class PushTokenAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_id',
        'platform',
        'updated_at',
    )
    search_fields = ('user_id', 'fcm_token')
    readonly_fields = ('created_at', 'updated_at')
