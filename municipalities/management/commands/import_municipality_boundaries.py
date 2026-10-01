import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from municipalities.boundary_osm import (
    EMPTY_POLYGON,
    boundary_has_coordinates,
    fetch_boundary_geometry,
)
from municipalities.models import Municipality
from sensors.models import Sensor


class Command(BaseCommand):
    help = (
        'Sync municipality names and store GeoJSON boundaries in the database '
        '(for the mobile app API; OSM fetch runs once on the server).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-sensor-names',
            action='store_true',
            help='Create/update Municipality rows from Sensor.operator_name values.',
        )
        parser.add_argument(
            '--link-sensors',
            action='store_true',
            help='Set Sensor.municipality FK from operator_name where missing.',
        )
        parser.add_argument(
            '--fetch-osm',
            action='store_true',
            help='Fetch missing boundaries from Nominatim (respects 1.1s delay).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-fetch OSM even when a boundary is already stored.',
        )
        parser.add_argument(
            '--names',
            help='Comma-separated municipality names (default: all in DB).',
        )
        parser.add_argument(
            '--geojson',
            type=str,
            help='Import boundaries from a GeoJSON FeatureCollection file.',
        )
        parser.add_argument(
            '--include-county',
            action='store_true',
            help='Also ensure a «Landkreis Hof» entry (county outline for the map).',
        )

    def handle(self, *args, **options):
        if options['geojson']:
            self._import_geojson(Path(options['geojson']))
            return

        created_names = 0
        if options['sync_sensor_names']:
            created_names = self._sync_from_sensors()

        if options['include_county']:
            Municipality.objects.get_or_create(
                name='Landkreis Hof',
                defaults={'geo_boundary': EMPTY_POLYGON},
            )

        if options['link_sensors']:
            linked = self._link_sensors()
            self.stdout.write(f'Linked {linked} sensor(s) to municipalities.')

        if options['fetch_osm']:
            updated, skipped, failed = self._fetch_osm(
                names=self._parse_names(options.get('names')),
                force=options['force'],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'OSM import done: {updated} updated, '
                    f'{skipped} skipped, {failed} failed.'
                )
            )
        elif created_names:
            self.stdout.write(
                f'Synced {created_names} municipality name(s). '
                'Run with --fetch-osm to download boundaries.'
            )

    def _parse_names(self, raw: str | None) -> list[str] | None:
        if not raw:
            return None
        return [part.strip() for part in raw.split(',') if part.strip()]

    def _sync_from_sensors(self) -> int:
        names = (
            Sensor.objects.exclude(operator_name='')
            .values_list('operator_name', flat=True)
            .distinct()
        )
        created = 0
        for name in names:
            cleaned = name.strip()
            if not cleaned:
                continue
            _, was_created = Municipality.objects.get_or_create(
                name=cleaned,
                defaults={'geo_boundary': EMPTY_POLYGON},
            )
            if was_created:
                created += 1
        return created

    def _link_sensors(self) -> int:
        linked = 0
        municipalities = {
            m.name: m for m in Municipality.objects.all()
        }
        for sensor in Sensor.objects.filter(municipality__isnull=True).exclude(
            operator_name=''
        ):
            municipality = municipalities.get(sensor.operator_name.strip())
            if municipality is None:
                continue
            sensor.municipality = municipality
            sensor.save(update_fields=['municipality'])
            linked += 1
        return linked

    def _fetch_osm(self, *, names: list[str] | None, force: bool) -> tuple[int, int, int]:
        queryset = Municipality.objects.all().order_by('name')
        if names:
            queryset = queryset.filter(name__in=names)

        updated = skipped = failed = 0
        for municipality in queryset:
            if (
                not force
                and boundary_has_coordinates(municipality.geo_boundary)
            ):
                skipped += 1
                continue

            geometry = fetch_boundary_geometry(municipality.name)
            if geometry is None:
                failed += 1
                self.stderr.write(
                    self.style.WARNING(f'No boundary found: {municipality.name}')
                )
                continue

            municipality.geo_boundary = geometry
            municipality.save(update_fields=['geo_boundary'])
            updated += 1
            self.stdout.write(f'  ✓ {municipality.name}')

        return updated, skipped, failed

    def _import_geojson(self, path: Path) -> None:
        if not path.exists():
            raise CommandError(f'File not found: {path}')

        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'Invalid JSON: {exc}') from exc

        features = []
        if data.get('type') == 'FeatureCollection':
            features = data.get('features') or []
        elif data.get('type') == 'Feature':
            features = [data]
        else:
            raise CommandError(
                'Expected GeoJSON FeatureCollection or Feature.'
            )

        imported = 0
        with transaction.atomic():
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                properties = feature.get('properties') or {}
                name = (
                    properties.get('name')
                    or properties.get('GEMEINDE')
                    or properties.get('gemeinde')
                )
                geometry = feature.get('geometry')
                if not name or not isinstance(geometry, dict):
                    continue
                if not boundary_has_coordinates(geometry):
                    continue
                Municipality.objects.update_or_create(
                    name=str(name).strip(),
                    defaults={'geo_boundary': geometry},
                )
                imported += 1

        self.stdout.write(
            self.style.SUCCESS(f'Imported {imported} municipality boundary(ies).')
        )
