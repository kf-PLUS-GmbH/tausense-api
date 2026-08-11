from rest_framework import serializers


class LorawanWebhookPayloadSerializer(serializers.Serializer):
    rxTime = serializers.DateTimeField(required=False)
    timestamp = serializers.DateTimeField(required=False)
    deviceEui = serializers.CharField(max_length=100)
    deviceName = serializers.CharField(required=False, allow_blank=True)
    air_temperature_radiation_shield = serializers.FloatField(required=False)
    air_temperature = serializers.FloatField(required=False)
    air_humidity_radiation_shield = serializers.FloatField(required=False)
    air_humidity = serializers.FloatField(required=False)
    surface_temperature = serializers.FloatField(required=False)
    dew_point = serializers.FloatField(required=False)
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)
    SID = serializers.CharField(required=False)
    battery_voltage = serializers.FloatField(required=False)
    sensor_temperature = serializers.FloatField(required=False)
    angle = serializers.FloatField(required=False)
    _headers = serializers.DictField(required=False)
    esGeoShape = serializers.DictField(required=False)

    def validate(self, attrs):
        if not attrs.get('timestamp') and not attrs.get('rxTime'):
            raise serializers.ValidationError('timestamp or rxTime is required.')
        if (
            attrs.get('air_temperature_radiation_shield') is None
            and attrs.get('air_temperature') is None
        ):
            raise serializers.ValidationError(
                'air_temperature_radiation_shield or air_temperature is required.'
            )
        if (
            attrs.get('air_humidity_radiation_shield') is None
            and attrs.get('air_humidity') is None
        ):
            raise serializers.ValidationError(
                'air_humidity_radiation_shield or air_humidity is required.'
            )
        if attrs.get('surface_temperature') is None:
            raise serializers.ValidationError('surface_temperature is required.')
        return attrs


class WebhookIngestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    reading_id = serializers.IntegerField()
    sensor_id = serializers.IntegerField()
    external_id = serializers.CharField()
    device_name = serializers.CharField(allow_blank=True)
    timestamp = serializers.DateTimeField()


class WebhookBulkIngestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    results = WebhookIngestResponseSerializer(many=True)
