from django.db import models


class UsageAnalyticsInstallation(models.Model):
    installation_id = models.UUIDField(unique=True, db_index=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    client_updated_at = models.DateTimeField(null=True, blank=True)
    days = models.JSONField(default=dict, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_upload_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'App-Nutzung (Installation)'
        verbose_name_plural = 'App-Nutzung'

    def __str__(self) -> str:
        return str(self.installation_id)

    @property
    def day_count(self) -> int:
        return len(self.days or {})
