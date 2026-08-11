from django.contrib import admin

from sensors.models import Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'device_name',
        'operator_name',
        'display_name',
        'external_id',
        'active',
    )
    list_filter = ('active', 'sensor_type', 'operator_name', 'municipality')
    search_fields = (
        'name',
        'device_name',
        'display_name',
        'operator_name',
        'location_description',
        'external_id',
    )
