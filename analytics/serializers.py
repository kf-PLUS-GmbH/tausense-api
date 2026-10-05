from rest_framework import serializers

from analytics.merge import valid_date_key


class UsageAnalyticsUploadSerializer(serializers.Serializer):
    schema_version = serializers.IntegerField()
    installation_id = serializers.UUIDField()
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    days = serializers.DictField(child=serializers.DictField(), allow_empty=True)

    def validate_schema_version(self, value: int) -> int:
        if value != 1:
            raise serializers.ValidationError('Only schema_version 1 is supported.')
        return value

    def validate_days(self, value: dict) -> dict:
        cleaned: dict = {}
        for day_key, day_payload in (value or {}).items():
            if not valid_date_key(day_key):
                raise serializers.ValidationError(
                    f'Invalid day key "{day_key}". Expected YYYY-MM-DD.',
                )
            if not isinstance(day_payload, dict):
                raise serializers.ValidationError(
                    f'Day "{day_key}" must be an object.',
                )
            cleaned[day_key] = day_payload
        return cleaned
