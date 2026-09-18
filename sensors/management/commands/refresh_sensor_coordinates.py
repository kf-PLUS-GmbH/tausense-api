from django.core.management.base import BaseCommand
from django.db import transaction

from sensors.models import Sensor
from sensors.services.coordinates import coordinates_from_device_name


class Command(BaseCommand):
    help = (
        'Set Sensor.latitude/longitude from device_name (-N…-E… pattern). '
        'Run after fixing webhook GPS handling if pins were wrong on the map.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print changes without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        skipped = 0

        with transaction.atomic():
            for sensor in Sensor.objects.exclude(device_name__isnull=True).exclude(device_name=''):
                coords = coordinates_from_device_name(sensor.device_name)
                if not coords:
                    skipped += 1
                    continue
                new_lat, new_lon = coords
                if sensor.latitude == new_lat and sensor.longitude == new_lon:
                    continue
                self.stdout.write(
                    f'id={sensor.id} {sensor.device_name}: '
                    f'was {sensor.latitude},{sensor.longitude} -> {new_lat},{new_lon}'
                )
                if not dry_run:
                    sensor.latitude = new_lat
                    sensor.longitude = new_lon
                    sensor.save(update_fields=['latitude', 'longitude', 'updated_at'])
                updated += 1
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f'Done: {updated} updated, {skipped} without -N/-E pattern in device_name.'
            )
        )
