from rest_framework import serializers

from core.utils import calculate_dew_point, calculate_trend
from drf_spectacular.utils import extend_schema_field
from readings.models import SensorReading


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
            'municipality',
            'timestamp',
            'air_temperature',
            'road_temperature',
            'humidity',
            'dew_point',
            'trend',
            'raw_data',
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
