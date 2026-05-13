from rest_framework import serializers


class DashboardWarningSerializer(serializers.Serializer):
    municipality = serializers.CharField(help_text='Municipality name.')
    warning_count = serializers.IntegerField(
        help_text='Number of sensors in warning state in this municipality.'
    )


class DashboardColdestSensorSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField()
    sensor_name = serializers.CharField()
    municipality = serializers.CharField()
    road_temperature = serializers.FloatField(help_text='Road surface temperature in °C.')
    air_temperature = serializers.FloatField(help_text='Air temperature in °C.')
    dew_point = serializers.FloatField(help_text='Computed dew point in °C.')
    timestamp = serializers.DateTimeField()


class CoordinatesSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class MapLatestReadingSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    air_temperature = serializers.FloatField(help_text='Air temperature in °C.')
    road_temperature = serializers.FloatField(help_text='Road surface temperature in °C.')
    humidity = serializers.FloatField(help_text='Relative humidity in percent.')
    dew_point = serializers.FloatField(help_text='Computed dew point in °C.')
    trend = serializers.ChoiceField(choices=['rising', 'stable', 'falling'])


class DashboardMapSensorSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField()
    sensor_name = serializers.CharField()
    municipality = serializers.CharField()
    coordinates = CoordinatesSerializer()
    latest_reading = MapLatestReadingSerializer()
    alert_status = serializers.ChoiceField(choices=['green', 'gray', 'red'])

