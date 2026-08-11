from rest_framework import serializers

from sensors.models import Sensor


class SensorSerializer(serializers.ModelSerializer):
    municipality_name = serializers.CharField(
        source='municipality.name',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Sensor
        fields = (
            'id',
            'name',
            'device_name',
            'operator_name',
            'display_name',
            'location_description',
            'what3words',
            'municipality',
            'municipality_name',
            'latitude',
            'longitude',
            'sensor_type',
            'active',
            'external_id',
            'created_at',
            'updated_at',
        )


class SensorOperatorSerializer(serializers.Serializer):
    operator_name = serializers.CharField()
    sensor_count = serializers.IntegerField()
