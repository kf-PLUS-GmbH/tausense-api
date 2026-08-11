from django.db import models
from django.utils import timezone
from municipalities.models import Municipality


class Sensor(models.Model):
    TYPE_STANDARD = 'standard'
    TYPE_ADDITIONAL = 'additional'
    TYPE_CHOICES = (
        (TYPE_STANDARD, 'Standard'),
        (TYPE_ADDITIONAL, 'Additional'),
    )

    name = models.CharField(max_length=255)
    device_name = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='Stable LoRaWAN deviceName, e.g. MUB-TPK-0001-N50.22764-E11.76708.',
    )
    operator_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Responsible municipality/organization from the metadata list.',
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Human-readable sensor label for maps and admin views.',
    )
    location_description = models.TextField(
        blank=True,
        help_text='Road section, station, crossing or other installation details.',
    )
    what3words = models.CharField(max_length=255, blank=True)
    municipality = models.ForeignKey(
        Municipality,
        on_delete=models.SET_NULL,
        related_name='sensors',
        null=True,
        blank=True,
        help_text='Optional; can be assigned later in admin. Not required for webhook ingestion.',
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sensor_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    active = models.BooleanField(default=True)
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'updated_at' not in update_fields:
            kwargs['update_fields'] = [*update_fields, 'updated_at']
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.external_id})'
