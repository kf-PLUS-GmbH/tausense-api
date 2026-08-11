from django.db import models


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
