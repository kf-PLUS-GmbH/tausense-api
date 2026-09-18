from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from readings.models import SensorReading
from sensors.models import Sensor


class Command(BaseCommand):
    help = (
        'Move readings from a duplicate webhook sensor into the imported sensor, '
        'then delete the duplicate. Use after audit_sensor_mapping.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            dest='from_id',
            type=int,
            required=True,
            help='Duplicate sensor id (webhook-only, will be deleted).',
        )
        parser.add_argument(
            '--into',
            dest='into_id',
            type=int,
            required=True,
            help='Sensor id to keep (usually from XLSX import).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without writing to the database.',
        )

    def handle(self, *args, **options):
        try:
            source = Sensor.objects.get(pk=options['from_id'])
            target = Sensor.objects.get(pk=options['into_id'])
        except Sensor.DoesNotExist as exc:
            raise CommandError(str(exc)) from exc

        reading_count = SensorReading.objects.filter(sensor=source).count()
        self.stdout.write(
            f'Merge sensor {source.id} ({source.device_name!r}, EUI={source.external_id}) '
            f'→ {target.id} ({target.device_name!r}, EUI={target.external_id})'
        )
        self.stdout.write(f'  Readings to move: {reading_count}')

        if options['dry_run']:
            self.stdout.write('Dry run – no changes.')
            return

        with transaction.atomic():
            SensorReading.objects.filter(sensor=source).update(sensor=target)
            updates = []
            if source.external_id and not target.external_id:
                target.external_id = source.external_id
                updates.append('external_id')
            if source.device_name and (
                not target.device_name
                or len(source.device_name) > len(target.device_name or '')
            ):
                target.device_name = source.device_name
                updates.append('device_name')
            if updates:
                target.save(update_fields=updates)
            source.delete()

        self.stdout.write(self.style.SUCCESS('Merge complete.'))
