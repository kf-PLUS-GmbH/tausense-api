from django.db import models
from django.utils.translation import gettext_lazy as _


class AppMaintenanceSettings(models.Model):
    """
    Singleton (always pk=1): global maintenance / info banner for the mobile app.
    """

    SINGLETON_PK = 1

    enabled = models.BooleanField(
        default=False,
        help_text=_('When on, the app shows the maintenance banner (subject to schedule below).'),
    )
    title = models.CharField(
        max_length=120,
        default='Wartungsarbeiten',
        help_text=_('Short headline in the app (e.g. “App in Wartung”).'),
    )
    message = models.TextField(
        blank=True,
        help_text=_('Longer explanation for users (German).'),
    )
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Optional: banner becomes active from this time (UTC stored, shown local in API).'),
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Optional: banner ends after this time; leave empty for open-ended.'),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('App-Wartungshinweis')
        verbose_name_plural = _('App-Wartungshinweis')

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> 'AppMaintenanceSettings':
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj
