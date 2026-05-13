from django.db import models
from municipalities.models import Municipality
from sensors.models import Sensor


class AlertRule(models.Model):
    THRESHOLD_TEMPERATURE = 'temperature'
    THRESHOLD_DEW_POINT = 'dew_point'
    THRESHOLD_CHOICES = (
        (THRESHOLD_TEMPERATURE, 'Temperature'),
        (THRESHOLD_DEW_POINT, 'Dew Point'),
    )

    OP_GT = 'gt'
    OP_LT = 'lt'
    OP_GTE = 'gte'
    OP_LTE = 'lte'
    OPERATOR_CHOICES = (
        (OP_GT, 'Greater than'),
        (OP_LT, 'Less than'),
        (OP_GTE, 'Greater than or equal'),
        (OP_LTE, 'Less than or equal'),
    )

    name = models.CharField(max_length=255)
    sensor = models.ForeignKey(
        Sensor,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='alert_rules',
    )
    municipality = models.ForeignKey(
        Municipality,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='alert_rules',
    )
    threshold_type = models.CharField(max_length=20, choices=THRESHOLD_CHOICES)
    operator = models.CharField(max_length=5, choices=OPERATOR_CHOICES)
    threshold_value = models.FloatField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AlertEvent(models.Model):
    SEVERITY_GREEN = 'green'
    SEVERITY_GRAY = 'gray'
    SEVERITY_RED = 'red'
    SEVERITY_CHOICES = (
        (SEVERITY_GREEN, 'Green'),
        (SEVERITY_GRAY, 'Gray'),
        (SEVERITY_RED, 'Red'),
    )

    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='events')
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='alert_events')
    triggered_at = models.DateTimeField()
    triggered_value = models.FloatField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)

    class Meta:
        ordering = ['-triggered_at']

    def __str__(self):
        return f'{self.rule.name} - {self.sensor.name}'
