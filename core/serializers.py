from rest_framework import serializers


class AppMaintenanceSerializer(serializers.Serializer):
    active = serializers.BooleanField(
        help_text='True when the app should show the maintenance banner now.',
    )
    state = serializers.ChoiceField(
        choices=['inactive', 'scheduled', 'active', 'ended'],
        help_text='inactive=off; scheduled=starts later; active=show banner; ended=past ends_at.',
    )
    title = serializers.CharField()
    message = serializers.CharField(allow_blank=True)
    starts_at = serializers.DateTimeField(allow_null=True)
    ends_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField()


class AppMaintenanceResponseSerializer(serializers.Serializer):
    app_maintenance = AppMaintenanceSerializer()


class DashboardWarningSerializer(serializers.Serializer):
    municipality = serializers.CharField(
        help_text='Municipality name.',
        allow_null=True,
    )
    warning_count = serializers.IntegerField(
        help_text='Number of sensors with any ice warning level (not "none") in this municipality.'
    )


class DashboardColdestSensorSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField()
    sensor_name = serializers.CharField()
    device_name = serializers.CharField(allow_blank=True)
    municipality = serializers.CharField(allow_null=True)
    road_temperature = serializers.FloatField(help_text='Road surface temperature in °C.')
    air_temperature = serializers.FloatField(help_text='Air temperature in °C.')
    dew_point = serializers.FloatField(help_text='Computed dew point in °C.')
    battery_voltage = serializers.FloatField(allow_null=True)
    timestamp = serializers.DateTimeField()


class CoordinatesSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class MapLatestReadingSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    device_name = serializers.CharField(allow_blank=True)
    air_temperature = serializers.FloatField(help_text='Air temperature in °C.')
    road_temperature = serializers.FloatField(help_text='Road surface temperature in °C.')
    humidity = serializers.FloatField(help_text='Relative humidity in percent.')
    air_temperature_radiation_shield = serializers.FloatField(allow_null=True)
    air_humidity_radiation_shield = serializers.FloatField(allow_null=True)
    air_temperature_unshielded = serializers.FloatField(allow_null=True)
    air_humidity_unshielded = serializers.FloatField(allow_null=True)
    dew_point = serializers.FloatField(help_text='Computed dew point in °C.')
    reported_dew_point = serializers.FloatField(allow_null=True)
    trend = serializers.ChoiceField(choices=['rising', 'stable', 'falling'])
    angle = serializers.FloatField(allow_null=True)
    sensor_temperature = serializers.FloatField(allow_null=True)
    battery_voltage = serializers.FloatField(allow_null=True)
    is_plausible = serializers.BooleanField(
        help_text='False when road/air/humidity are outside configured physical limits.',
    )


class MapDisplayReadingSerializer(MapLatestReadingSerializer):
    is_stale = serializers.BooleanField(
        help_text='True when display_reading is an older plausible row (latest is invalid).',
    )


class DashboardMapSensorSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField()
    sensor_name = serializers.CharField()
    device_name = serializers.CharField(allow_blank=True, allow_null=True)
    operator_name = serializers.CharField(allow_blank=True)
    municipality = serializers.CharField(allow_null=True)
    coordinates = CoordinatesSerializer()
    updated_at = serializers.DateTimeField()
    measurement_status = serializers.ChoiceField(
        choices=['ok', 'unreliable', 'maintenance'],
        help_text='Whether the UI should trust latest_reading or show a status banner.',
    )
    status_message = serializers.CharField(
        allow_null=True,
        help_text='German hint for unreliable or maintenance; null when measurement_status is ok.',
    )
    latest_reading = MapLatestReadingSerializer(
        allow_null=True,
        help_text='Most recent stored row (may be implausible).',
    )
    display_reading = MapDisplayReadingSerializer(
        allow_null=True,
        help_text='Last plausible row when measurement_status is not ok; null when ok (use latest_reading).',
    )
    ice_warning_level = serializers.ChoiceField(
        choices=['none', 'possible_slip', 'increased_ice', 'acute_ice'],
        help_text='Ice/slip risk level derived from road temperature, dew point and humidity.',
    )
    ice_warning_label = serializers.CharField(
        help_text='German label for the ice warning level.',
    )
    alert_status = serializers.ChoiceField(
        choices=['green', 'yellow', 'orange', 'red', 'gray'],
        help_text='Map marker color; gray when maintenance or no displayable values.',
    )

