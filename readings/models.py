from django.db import models
from sensors.models import Sensor


class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.DateTimeField(db_index=True)
    air_temperature = models.FloatField()
    road_temperature = models.FloatField()
    humidity = models.FloatField(help_text='Relative humidity in percent.')
    raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor', '-timestamp']),
            models.Index(fields=['sensor', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.sensor_id} @ {self.timestamp.isoformat()}'
