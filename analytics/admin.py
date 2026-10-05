from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from analytics.aggregation import (
    build_dashboard,
    build_installation_report,
    period_days_from_request,
)
from analytics.models import UsageAnalyticsInstallation
from core.admin_mixins import TauSenseModelAdmin
from sensors.models import Sensor


def _enrich_sensor_labels(metrics) -> None:
    ids = []
    for metric in metrics:
        if str(metric.key).isdigit():
            ids.append(int(metric.key))
    if not ids:
        return
    names = {
        sensor.pk: sensor.name
        for sensor in Sensor.objects.filter(pk__in=ids).only('pk', 'name')
    }
    for metric in metrics:
        if str(metric.key).isdigit():
            sensor_id = int(metric.key)
            name = names.get(sensor_id)
            if name:
                metric.label = f'{name} (#{sensor_id})'


def _period_choices():
    return (
        (7, '7 Tage'),
        (30, '30 Tage'),
        (90, '90 Tage'),
    )


@admin.register(UsageAnalyticsInstallation)
class UsageAnalyticsInstallationAdmin(TauSenseModelAdmin):
    change_form_template = 'admin/analytics/installation_change_form.html'

    list_display = (
        'installation_id_short',
        'schema_version',
        'day_count_display',
        'client_updated_at',
        'last_upload_at',
    )
    search_fields = ('installation_id',)
    readonly_fields = (
        'installation_id',
        'schema_version',
        'client_updated_at',
        'first_seen_at',
        'last_upload_at',
    )
    fieldsets = (
        (
            'Metadaten',
            {
                'fields': readonly_fields,
            },
        ),
    )

    @admin.display(description='Installation')
    def installation_id_short(self, obj: UsageAnalyticsInstallation) -> str:
        value = str(obj.installation_id)
        return f'{value[:8]}…'

    @admin.display(description='Tage gespeichert')
    def day_count_display(self, obj: UsageAnalyticsInstallation) -> int:
        return obj.day_count

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'dashboard/',
                self.admin_site.admin_view(self.dashboard_view),
                name='analytics_usageanalyticsinstallation_dashboard',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        if request.GET.get('raw') == '1':
            extra_context = extra_context or {}
            extra_context['show_dashboard_link'] = True
            return super().changelist_view(request, extra_context)

        query = request.GET.urlencode()
        url = reverse('admin:analytics_usageanalyticsinstallation_dashboard')
        if query:
            url = f'{url}?{query}'
        return HttpResponseRedirect(url)

    def dashboard_view(self, request):
        period = period_days_from_request(request.GET.get('period'))
        queryset = UsageAnalyticsInstallation.objects.all()
        report = build_dashboard(queryset, period_days=period)
        _enrich_sensor_labels(report.sensors)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'App-Nutzung',
            'report': report,
            'period_choices': _period_choices(),
        }
        return render(request, 'admin/analytics/dashboard.html', context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        period = period_days_from_request(request.GET.get('period'))
        report = build_installation_report(obj.days or {}, period_days=period)
        report.installation_id = str(obj.installation_id)
        _enrich_sensor_labels(report.sensors)

        max_sessions = max((point.sessions for point in report.sessions_series), default=0) or 1
        extra_context.update(
            {
                'report': report,
                'period_choices': _period_choices(),
                'max_sessions_in_day': max_sessions,
            },
        )
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
