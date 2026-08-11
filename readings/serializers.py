from rest_framework import serializers

from core.utils import calculate_dew_point, calculate_trend
from drf_spectacular.utils import extend_schema_field
from readings.models import SensorReading


class ReadingHistoryPointSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    air_temperature = serializers.FloatField(help_text='Air temperature in °C.')
    road_temperature = serializers.FloatField(help_text='Road surface temperature in °C.')
    humidity = serializers.FloatField(help_text='Relative humidity in percent.')
    air_temperature_radiation_shield = serializers.FloatField(allow_null=True)
    air_humidity_radiation_shield = serializers.FloatField(allow_null=True)
    air_temperature_unshielded = serializers.FloatField(allow_null=True)
    air_humidity_unshielded = serializers.FloatField(allow_null=True)
    dew_point = serializers.FloatField(help_text='Computed dew point in °C.')
    reported_dew_point = serializers.FloatField(allow_null=True)
    angle = serializers.FloatField(allow_null=True)
    sensor_temperature = serializers.FloatField(allow_null=True)
    battery_voltage = serializers.FloatField(allow_null=True)
    ice_warning_level = serializers.ChoiceField(
        choices=['none', 'possible_slip', 'increased_ice', 'acute_ice'],
    )
    alert_status = serializers.ChoiceField(choices=['green', 'yellow', 'orange', 'red'])


class ReadingHistoryResponseSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField()
    sensor_name = serializers.CharField()
    from_timestamp = serializers.DateTimeField(source='from')
    to_timestamp = serializers.DateTimeField(source='to')
    days = serializers.IntegerField(help_text='Selected or computed day span (max 14).')
    count = serializers.IntegerField()
    points = ReadingHistoryPointSerializer(many=True)


class SensorReadingSerializer(serializers.ModelSerializer):
    dew_point = serializers.SerializerMethodField()
    trend = serializers.SerializerMethodField()
    municipality = serializers.IntegerField(
        source='sensor.municipality_id',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = SensorReading
        fields = (
            'id',
            'sensor',
            'device_name',
            'municipality',
            'timestamp',
            'air_temperature',
            'road_temperature',
            'humidity',
            'air_temperature_radiation_shield',
            'air_humidity_radiation_shield',
            'air_temperature_unshielded',
            'air_humidity_unshielded',
            'dew_point',
            'reported_dew_point',
            'trend',
            'angle',
            'sensor_temperature',
            'battery_voltage',
            'latitude',
            'longitude',
        )

    @extend_schema_field(serializers.FloatField())
    def get_dew_point(self, obj) -> float:
        return calculate_dew_point(obj.air_temperature, obj.humidity)

    @extend_schema_field(serializers.ChoiceField(choices=['rising', 'stable', 'falling']))
    def get_trend(self, obj) -> str:
        prev = (
            SensorReading.objects.filter(sensor=obj.sensor, timestamp__lt=obj.timestamp)
            .order_by('-timestamp')
            .values_list('air_temperature', flat=True)
            .first()
        )
        return calculate_trend(obj.air_temperature, prev)
