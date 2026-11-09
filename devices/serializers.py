from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from devices.client_id import resolve_client_id
from devices.models import AlertPreference, PushToken
from devices.notification_schedule import (
    default_notification_schedule,
    normalize_notification_schedule,
    parse_hhmm_minutes,
)


class NotificationScheduleSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    start = serializers.CharField(max_length=5)
    end = serializers.CharField(max_length=5)
    timezone = serializers.CharField(max_length=64)

    def validate(self, attrs):
        try:
            parse_hhmm_minutes(attrs['start'])
            parse_hhmm_minutes(attrs['end'])
        except ValueError as exc:
            raise serializers.ValidationError({'start': str(exc), 'end': str(exc)}) from exc
        tz_name = attrs['timezone'].strip()
        if not tz_name:
            raise serializers.ValidationError({'timezone': 'Timezone must not be empty.'})
        try:
            ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError(
                {'timezone': f'Unknown IANA timezone: {tz_name}'}
            ) from exc
        attrs['timezone'] = tz_name
        return attrs


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
    notification_schedule = NotificationScheduleSerializer(required=False, allow_null=True)

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

        defaults = {
            'severity_filter': data['severity_filter'],
            'notifications_enabled': data['notifications_enabled'],
            'selected_municipality': municipality,
            'selected_sensor_ids': data.get('selected_sensor_ids') or [],
        }
        raw_schedule = data.get('notification_schedule')
        if raw_schedule is not None:
            defaults['notification_schedule'] = normalize_notification_schedule(raw_schedule)

        preference, _ = AlertPreference.objects.update_or_create(
            user_id=data['user_id'],
            defaults=defaults,
        )
        return preference


class AlertPreferenceResponseSerializer(serializers.ModelSerializer):
    notification_schedule = serializers.SerializerMethodField()

    class Meta:
        model = AlertPreference
        fields = [
            'user_id',
            'severity_filter',
            'notifications_enabled',
            'selected_municipality',
            'selected_sensor_ids',
            'notification_schedule',
            'created_at',
            'updated_at',
        ]

    def get_notification_schedule(self, obj):
        return normalize_notification_schedule(obj.notification_schedule)


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
