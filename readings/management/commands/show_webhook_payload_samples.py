import json

from django.core.management.base import BaseCommand

from readings.models import SensorReading


class Command(BaseCommand):
    help = (
        'Print raw_data from the most recent sensor readings (as stored at webhook ingest). '
        'Useful to compare old vs new sender format.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=3,
            help='Number of readings to show (default: 3).',
        )

    def handle(self, *args, **options):
        limit = max(1, options['limit'])
        readings = (
            SensorReading.objects.select_related('sensor')
            .order_by('-timestamp')[:limit]
        )
        if not readings:
            self.stdout.write('No readings in database.')
            return

        for reading in readings:
            self.stdout.write(
                f'\n--- reading id={reading.id} '
                f'timestamp={reading.timestamp.isoformat()} '
                f'sensor={reading.sensor_id} '
                f'device_name={reading.device_name!r} ---'
            )
            payload = reading.raw_data
            if payload is None:
                self.stdout.write('(raw_data is empty)')
                continue
            self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
