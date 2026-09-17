from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from django.utils import timezone

from readings.models import SensorReading
from sensors.models import Sensor


class Command(BaseCommand):
    help = (
        'Check sensor registry: XLSX import (device_name, Gemeinde) vs LoRaWAN '
        'webhook linkage (external_id / EUI) and recent readings.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--stale-hours',
            type=int,
            default=48,
            help='Flag sensors with no reading in this many hours (default: 48).',
        )

    def handle(self, *args, **options):
        stale_cutoff = timezone.now() - timedelta(hours=max(1, options['stale_hours']))
        qs = (
            Sensor.objects.annotate(
                reading_count=Count('readings'),
                last_reading_at=Max('readings__timestamp'),
            )
            .order_by('device_name', 'id')
        )

        total = qs.count()
        with_eui = qs.exclude(external_id__isnull=True).exclude(external_id='').count()
        with_gemeinde = qs.filter(municipality__isnull=False).count()
        with_operator = qs.exclude(operator_name='').count()
        active = qs.filter(active=True).count()

        self.stdout.write(self.style.MIGRATE_HEADING('Summary'))
        self.stdout.write(f'  Sensors total:        {total}')
        self.stdout.write(f'  Active:               {active}')
        self.stdout.write(f'  With EUI (external_id): {with_eui}')
        self.stdout.write(f'  With municipality FK: {with_gemeinde}')
        self.stdout.write(f'  With operator_name:   {with_operator}')
        self.stdout.write('')

        issues_no_eui = []
        issues_webhook_only = []
        issues_stale = []
        issues_name_mismatch = []
        issues_no_readings = []

        for sensor in qs:
            eui = (sensor.external_id or '').strip()
            has_import_meta = bool(sensor.operator_name or sensor.display_name)

            if not eui and sensor.reading_count > 0:
                issues_no_eui.append(sensor)
            elif eui and not has_import_meta and not sensor.municipality_id:
                issues_webhook_only.append(sensor)

            if sensor.reading_count == 0:
                issues_no_readings.append(sensor)
            elif sensor.last_reading_at and sensor.last_reading_at < stale_cutoff:
                issues_stale.append(sensor)

            latest = (
                SensorReading.objects.filter(sensor_id=sensor.id)
                .order_by('-timestamp')
                .values_list('device_name', flat=True)
                .first()
            )
            if (
                latest
                and sensor.device_name
                and latest.strip() != sensor.device_name.strip()
            ):
                issues_name_mismatch.append((sensor, latest))

        self._section(
            'OK – linked (EUI + import metadata)',
            [
                s
                for s in qs
                if (s.external_id or '').strip()
                and (s.operator_name or s.display_name or s.municipality_id)
                and s.reading_count > 0
            ],
            lambda s: (
                f'{s.device_name}  EUI={s.external_id}  '
                f'operator={s.operator_name or "-"}  readings={s.reading_count}'
            ),
            limit=15,
            ok=True,
        )

        self._section(
            'Import in DB but no EUI yet (no webhook match by device_name?)',
            issues_no_eui,
            lambda s: (
                f'id={s.id}  device_name={s.device_name!r}  '
                f'readings={s.reading_count}  operator={s.operator_name or "-"}'
            ),
        )

        self._section(
            'Webhook-only (EUI set, missing import/Gemeinde metadata)',
            issues_webhook_only,
            lambda s: (
                f'id={s.id}  EUI={s.external_id}  device_name={s.device_name!r}  '
                f'readings={s.reading_count}'
            ),
        )

        self._section(
            'device_name in DB ≠ latest reading device_name',
            issues_name_mismatch,
            lambda pair: (
                f'id={pair[0].id}  sensor.device_name={pair[0].device_name!r}  '
                f'reading.device_name={pair[1]!r}  EUI={pair[0].external_id}'
            ),
        )

        self._section(
            f'No reading in last {options["stale_hours"]}h (but has readings historically)',
            issues_stale,
            lambda s: (
                f'{s.device_name or s.external_id}  last={s.last_reading_at}  '
                f'EUI={s.external_id or "-"}'
            ),
        )

        self._section(
            'Never received a reading',
            issues_no_readings,
            lambda s: (
                f'id={s.id}  device_name={s.device_name!r}  EUI={s.external_id or "-"}  '
                f'operator={s.operator_name or "-"}'
            ),
        )

        self.stdout.write('')
        self.stdout.write(
            'Linking rule: webhook sets EUI on existing sensor when '
            'deviceInfo.deviceName equals Sensor.device_name (from XLSX Standortbezeichnung). '
            'Names must match exactly.'
        )

    def _section(self, title, items, fmt, limit=25, ok=False):
        self.stdout.write('')
        if ok:
            self.stdout.write(self.style.SUCCESS(f'=== {title} ({len(items)}) ==='))
        else:
            style = self.style.WARNING if items else self.style.SUCCESS
            self.stdout.write(style(f'=== {title} ({len(items)}) ==='))
        if not items:
            self.stdout.write('  (none)')
            return
        for item in items[:limit]:
            self.stdout.write(f'  - {fmt(item)}')
        if len(items) > limit:
            self.stdout.write(f'  … and {len(items) - limit} more')
