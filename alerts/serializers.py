from rest_framework import serializers

from alerts.models import AlertEvent, AlertRule


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = (
            'id',
            'name',
            'sensor',
            'municipality',
            'threshold_type',
            'operator',
            'threshold_value',
            'active',
        )


class AlertEventSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    sensor_name = serializers.CharField(source='sensor.name', read_only=True)

    class Meta:
        model = AlertEvent
        fields = (
            'id',
            'rule',
            'rule_name',
            'sensor',
            'sensor_name',
            'triggered_at',
            'triggered_value',
            'severity',
        )
