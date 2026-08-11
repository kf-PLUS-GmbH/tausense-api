from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from municipalities.models import Municipality
from readings.models import SensorReading
from sensors.models import Sensor


class Command(BaseCommand):
    help = 'Seed minimal demo data for Taupunktsensorik API.'

    def handle(self, *args, **options):
        municipality, _ = Municipality.objects.get_or_create(
            name='Hof',
            defaults={
                'geo_boundary': {
                    'type': 'Polygon',
                    'coordinates': [[[11.9, 50.28], [11.98, 50.28], [11.98, 50.34], [11.9, 50.28]]],
                }
            },
        )

        sensors = []
        for idx in range(1, 6):
            sensor, _ = Sensor.objects.get_or_create(
                external_id=f'HOF-{idx:03d}',
                defaults={
                    'name': f'Hof Sensor {idx}',
                    'municipality': municipality,
                    'latitude': 50.29 + (idx * 0.005),
                    'longitude': 11.91 + (idx * 0.004),
                    'sensor_type': Sensor.TYPE_STANDARD,
                    'active': True,
                },
            )
            sensors.append(sensor)

        now = timezone.now()
        for sensor in sensors:
            for minutes in range(0, 120, 15):
                ts = now - timedelta(minutes=minutes)
                SensorReading.objects.get_or_create(
                    sensor=sensor,
                    timestamp=ts,
                    defaults={
                        'device_name': sensor.name,
                        'air_temperature': round(random.uniform(-3.0, 3.0), 2),
                        'road_temperature': round(random.uniform(-5.0, 2.0), 2),
                        'humidity': round(random.uniform(70.0, 98.0), 2),
                        'air_temperature_radiation_shield': round(random.uniform(-3.0, 3.0), 2),
                        'air_humidity_radiation_shield': round(random.uniform(70.0, 98.0), 2),
                        'air_temperature_unshielded': round(random.uniform(-2.0, 4.0), 2),
                        'air_humidity_unshielded': round(random.uniform(65.0, 95.0), 2),
                        'reported_dew_point': round(random.uniform(-5.0, 2.0), 2),
                        'angle': random.randint(35, 55),
                        'sensor_temperature': round(random.uniform(-3.0, 3.0), 2),
                        'battery_voltage': round(random.uniform(2.5, 3.1), 2),
                        'latitude': sensor.latitude,
                        'longitude': sensor.longitude,
                    },
                )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
