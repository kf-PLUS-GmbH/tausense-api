from django.db import models
from sensors.models import Sensor


class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    device_name = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    air_temperature = models.FloatField()
    road_temperature = models.FloatField()
    humidity = models.FloatField(help_text='Relative humidity in percent.')
    air_temperature_radiation_shield = models.FloatField(null=True, blank=True)
    air_humidity_radiation_shield = models.FloatField(null=True, blank=True)
    air_temperature_unshielded = models.FloatField(null=True, blank=True)
    air_humidity_unshielded = models.FloatField(null=True, blank=True)
    reported_dew_point = models.FloatField(
        null=True,
        blank=True,
        help_text='Dew point as reported by upstream payload; API dew_point is computed.',
    )
    angle = models.FloatField(null=True, blank=True)
    sensor_temperature = models.FloatField(null=True, blank=True)
    battery_voltage = models.FloatField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor', '-timestamp']),
            models.Index(fields=['sensor', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.sensor_id} @ {self.timestamp.isoformat()}'
