from django.db import models


class Municipality(models.Model):
    name = models.CharField(max_length=255, unique=True)
    geo_boundary = models.JSONField(
        help_text='GeoJSON polygon or multipolygon describing municipality border.'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
