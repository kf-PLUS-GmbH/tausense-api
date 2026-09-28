from django.contrib import admin

from core.admin_mixins import TauSenseModelAdmin
from readings.models import SensorReading


@admin.register(SensorReading)
class SensorReadingAdmin(TauSenseModelAdmin):
    list_display = (
        'sensor',
        'timestamp',
        'air_temperature',
        'road_temperature',
        'humidity',
    )
    list_filter = ('sensor',)
    search_fields = ('device_name',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('raw_data',)
