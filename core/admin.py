from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect
from django.urls import reverse

from core.admin_mixins import TauSenseModelAdmin
from core.models import AppMaintenanceSettings

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(AppMaintenanceSettings)
class AppMaintenanceSettingsAdmin(TauSenseModelAdmin):
    list_display = ('enabled', 'title', 'starts_at', 'ends_at', 'updated_at')
    fieldsets = (
        (
            None,
            {
                'description': (
                    'Steuert einen Hinweis in der mobilen App (nicht die Einzel-Sensor-Wartung). '
                    '„Aktiv“ schaltet den Hinweis ein; optional mit Start- und Endzeit.'
                ),
                'fields': ('enabled', 'title', 'message', 'starts_at', 'ends_at', 'updated_at'),
            },
        ),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        if AppMaintenanceSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = AppMaintenanceSettings.load()
        return redirect(
            reverse('admin:core_appmaintenancesettings_change', args=[obj.pk]),
        )
