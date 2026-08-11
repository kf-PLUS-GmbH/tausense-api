from rest_framework import serializers

from devices.client_id import resolve_client_id
from devices.models import AlertPreference, PushToken


class AlertPreferenceSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    severity_filter = serializers.ChoiceField(choices=AlertPreference.SEVERITY_FILTER_CHOICES)
    notifications_enabled = serializers.BooleanField()
    selected_municipality = serializers.CharField(
        max_length=255,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    selected_sensor_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        request = self.context.get('request')
        user_id = resolve_client_id(request, self.initial_data)
        if not user_id:
            raise serializers.ValidationError(
                {
                    'user_id': (
                        'Provide user_id/device_id in the body or send X-User-Id / X-Device-Id header.'
                    )
                }
            )
        attrs['user_id'] = user_id
        return attrs

    def save(self) -> AlertPreference:
        data = self.validated_data
        municipality = data.get('selected_municipality')
        if municipality == '':
            municipality = None

        preference, _ = AlertPreference.objects.update_or_create(
            user_id=data['user_id'],
            defaults={
                'severity_filter': data['severity_filter'],
                'notifications_enabled': data['notifications_enabled'],
                'selected_municipality': municipality,
                'selected_sensor_ids': data.get('selected_sensor_ids') or [],
            },
        )
        return preference


class AlertPreferenceResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertPreference
        fields = [
            'user_id',
            'severity_filter',
            'notifications_enabled',
            'selected_municipality',
            'selected_sensor_ids',
            'created_at',
            'updated_at',
        ]


class PushTokenSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    fcm_token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=PushToken.PLATFORM_CHOICES)

    def validate(self, attrs):
        request = self.context.get('request')
        user_id = resolve_client_id(request, self.initial_data)
        if not user_id:
            raise serializers.ValidationError(
                {
                    'user_id': (
                        'Provide user_id/device_id in the body or send X-User-Id / X-Device-Id header.'
                    )
                }
            )
        attrs['user_id'] = user_id
        return attrs

    def validate_fcm_token(self, value):
        token = value.strip()
        if not token:
            raise serializers.ValidationError('FCM token must not be empty.')
        return token

    def save(self) -> PushToken:
        data = self.validated_data
        token, _ = PushToken.objects.update_or_create(
            fcm_token=data['fcm_token'],
            defaults={
                'user_id': data['user_id'],
                'platform': data['platform'],
            },
        )
        return token


class PushTokenResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = [
            'id',
            'user_id',
            'fcm_token',
            'platform',
            'created_at',
            'updated_at',
        ]


class TestPushSerializer(serializers.Serializer):
    device_token = serializers.CharField(max_length=512)
    sensor_id = serializers.IntegerField(min_value=1)
    alert_status = serializers.ChoiceField(choices=['green', 'yellow', 'orange', 'red'])
    sensor_name = serializers.CharField(max_length=255)
    municipality_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    title = serializers.CharField(max_length=255)
    body = serializers.CharField(max_length=500)
