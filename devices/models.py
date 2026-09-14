from django.db import models

from core.ice_warning import ICE_WARNING_LEVELS
from sensors.models import Sensor


class AlertPreference(models.Model):
    SEVERITY_ORANGE = 'orange'
    SEVERITY_RED = 'red'
    SEVERITY_FILTER_CHOICES = (
        (SEVERITY_ORANGE, 'Orange and red'),
        (SEVERITY_RED, 'Red only'),
    )

    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    severity_filter = models.CharField(max_length=10, choices=SEVERITY_FILTER_CHOICES)
    notifications_enabled = models.BooleanField(default=True)
    selected_municipality = models.CharField(max_length=255, null=True, blank=True)
    selected_sensor_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Preferences for {self.user_id}'


class PushToken(models.Model):
    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'
    PLATFORM_CHOICES = (
        (PLATFORM_ANDROID, 'Android'),
        (PLATFORM_IOS, 'iOS'),
    )

    user_id = models.CharField(max_length=255, db_index=True)
    fcm_token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'push_tokens'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f'{self.user_id} ({self.platform})'


class PushNotificationState(models.Model):
    user_id = models.CharField(max_length=255, db_index=True)
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='push_notification_states',
    )
    last_level = models.CharField(max_length=20, choices=[(level, level) for level in ICE_WARNING_LEVELS])
    last_sent_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'sensor'], name='unique_push_state_per_user_sensor'),
        ]
        indexes = [
            models.Index(fields=['sensor', 'user_id']),
        ]

    def __str__(self):
        return f'{self.user_id} / sensor {self.sensor_id} @ {self.last_level}'


class PushDigestState(models.Model):
    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    last_worst_severity = models.PositiveSmallIntegerField(default=0)
    last_sensor_count = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user_id} digest @ severity {self.last_worst_severity} ({self.last_sensor_count} sensors)'
