from rest_framework import serializers

from sensors.models import Sensor


class SensorSerializer(serializers.ModelSerializer):
    municipality_name = serializers.CharField(source='municipality.name', read_only=True)

    class Meta:
        model = Sensor
        fields = (
            'id',
            'name',
            'municipality',
            'municipality_name',
            'latitude',
            'longitude',
            'sensor_type',
            'active',
            'external_id',
        )
