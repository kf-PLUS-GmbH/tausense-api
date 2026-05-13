from django.db import models
from municipalities.models import Municipality


class Sensor(models.Model):
    TYPE_STANDARD = 'standard'
    TYPE_ADDITIONAL = 'additional'
    TYPE_CHOICES = (
        (TYPE_STANDARD, 'Standard'),
        (TYPE_ADDITIONAL, 'Additional'),
    )

    name = models.CharField(max_length=255)
    municipality = models.ForeignKey(
        Municipality,
        on_delete=models.CASCADE,
        related_name='sensors',
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    sensor_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    active = models.BooleanField(default=True)
    external_id = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.external_id})'
