from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.ice_warning import (
    ICE_WARNING_ACUTE_ICE,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_LABELS,
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
    alert_status_for_level,
    evaluate_ice_warning,
)
from core.services import latest_readings_with_previous
from core.utils import calculate_dew_point
from devices.models import AlertPreference, PushToken
from devices.services.subscriptions import (
    find_subscribed_push_tokens,
    matches_severity_filter,
    matches_subscription,
    notify_sensor_ice_warning,
    send_broadcast_test_pushes,
)
from municipalities.models import Municipality
from readings.models import SensorReading
from sensors.models import Sensor

READING_PRESETS = {
    ICE_WARNING_NONE: {
        'air_temperature': 5.0,
        'road_temperature': 5.0,
        'humidity': 70.0,
    },
    ICE_WARNING_POSSIBLE_SLIP: {
        'air_temperature': 1.5,
        'road_temperature': 1.5,
        'humidity': 85.0,
    },
    ICE_WARNING_INCREASED_ICE: {
        'air_temperature': 0.5,
        'road_temperature': 0.5,
        'humidity': 88.0,
    },
    ICE_WARNING_ACUTE_ICE: {
        'air_temperature': 0.0,
        'road_temperature': 0.0,
        'humidity': 100.0,
    },
}

STATUS_TO_LEVEL = {
    'green': ICE_WARNING_NONE,
    'yellow': ICE_WARNING_POSSIBLE_SLIP,
    'orange': ICE_WARNING_INCREASED_ICE,
    'red': ICE_WARNING_ACUTE_ICE,
}


class Command(BaseCommand):
    help = 'Create test alert readings and/or send test push notifications.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List push tokens, preferences and current sensor alert status (incl. green sensors for testing).',
        )
        parser.add_argument(
            '--broadcast',
            choices=['green', 'yellow', 'orange', 'red'],
            help='Send a test push directly to registered tokens (ignores preference filters).',
        )
        parser.add_argument(
            '--simulate',
            choices=['possible_slip', 'increased_ice', 'acute_ice'],
            help='Create test readings and trigger the normal push flow (with --force).',
        )
        parser.add_argument(
            '--all-colors',
            action='store_true',
            help='With --broadcast: send green, yellow, orange and red test pushes.',
        )
        parser.add_argument(
            '--user-id',
            help='Limit pushes to one local app user id.',
        )
        parser.add_argument(
            '--sensor-id',
            type=int,
            help='Sensor to use for simulated readings.',
        )
        parser.add_argument(
            '--setup-demo',
            action='store_true',
            help='Ensure a demo sensor exists for push testing.',
        )
        parser.add_argument(
            '--prepare-user',
            help='Update alert preferences for this user to match the test sensor (dev/testing only).',
        )
        parser.add_argument(
            '--area',
            help='With --list: only show sensors for this municipality/operator name.',
        )

    def handle(self, *args, **options):
        if options['list']:
            self._list_registrations(area=options.get('area'))
            return

        if options['setup_demo']:
            sensor = self._ensure_demo_sensor()
            self.stdout.write(self.style.SUCCESS(f'Demo sensor ready: id={sensor.id}, name={sensor.name}'))

        if options['broadcast']:
            self._broadcast(options)
            return

        if options['simulate']:
            self._simulate(options)
            return

        if not options['setup_demo']:
            raise CommandError(
                'Use one of: --list, --broadcast, --simulate, --setup-demo. '
                'Example: python manage.py trigger_test_alert_push --broadcast red'
            )

    def _list_registrations(self, area=None):
        tokens = PushToken.objects.all().order_by('-updated_at')
        preferences = AlertPreference.objects.all().order_by('-updated_at')

        self.stdout.write('Push tokens:')
        if not tokens:
            self.stdout.write('  (none — register via POST /api/v1/push-tokens/ from the app)')
        for token in tokens:
            self.stdout.write(
                f'  user_id={token.user_id} platform={token.platform} '
                f'token={token.fcm_token[:16]}... updated={token.updated_at.isoformat()}'
            )

        self.stdout.write('\nAlert preferences:')
        if not preferences:
            self.stdout.write('  (none — save via POST /api/v1/alerts/preferences/ from the app)')
        for pref in preferences:
            self.stdout.write(
                f'  user_id={pref.user_id} filter={pref.severity_filter} '
                f'enabled={pref.notifications_enabled} municipality={pref.selected_municipality!r} '
                f'sensors={pref.selected_sensor_ids}'
            )

        self._list_sensor_alert_status(preferences, area=area)

    def _sensor_area_label(self, sensor):
        if sensor.municipality_id:
            return sensor.municipality.name
        if sensor.operator_name:
            return sensor.operator_name
        return '-'

    def _matches_area_filter(self, sensor, area):
        if not area:
            return True
        area_lower = area.lower()
        labels = [
            sensor.municipality.name if sensor.municipality else '',
            sensor.operator_name or '',
        ]
        return any(area_lower in label.lower() for label in labels if label)

    def _list_sensor_alert_status(self, preferences, area=None):
        readings = latest_readings_with_previous().select_related('sensor', 'sensor__municipality')
        grouped = {
            'green': [],
            'yellow': [],
            'orange': [],
            'red': [],
        }

        for reading in readings:
            sensor = reading.sensor
            if not self._matches_area_filter(sensor, area):
                continue

            dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
            level = evaluate_ice_warning(reading.road_temperature, dew_point, reading.humidity)
            alert_status = alert_status_for_level(level)
            grouped[alert_status].append(
                {
                    'sensor_id': sensor.id,
                    'name': sensor.display_name or sensor.name,
                    'area': self._sensor_area_label(sensor),
                    'road': reading.road_temperature,
                    'level': level,
                    'label': ICE_WARNING_LABELS[level],
                }
            )

        area_label = f' (filtered by area={area!r})' if area else ''
        self.stdout.write(f'\nSensor alert status (latest readings){area_label}:')
        self.stdout.write(
            f'  green={len(grouped["green"])} yellow={len(grouped["yellow"])} '
            f'orange={len(grouped["orange"])} red={len(grouped["red"])}'
        )

        self.stdout.write('\nGreen sensors (good starting point for --simulate tests):')
        if not grouped['green']:
            self.stdout.write('  (none — all matching sensors currently have a warning level)')
        green_items = sorted(grouped['green'], key=lambda row: (row['area'], row['name']))
        display_limit = 30
        for item in green_items[:display_limit]:
            self.stdout.write(
                f'  id={item["sensor_id"]} area={item["area"]!r} '
                f'name={item["name"]!r} road={item["road"]}C'
            )
            self.stdout.write(
                f'    test: python manage.py trigger_test_alert_push '
                f'--simulate acute_ice --sensor-id {item["sensor_id"]}'
            )
        if len(green_items) > display_limit:
            self.stdout.write(f'  ... and {len(green_items) - display_limit} more green sensors')
            self.stdout.write('  tip: narrow with --area Stammbach')

        for status in ('yellow', 'orange', 'red'):
            if not grouped[status]:
                continue
            self.stdout.write(f'\n{status.capitalize()} sensors:')
            for item in sorted(grouped[status], key=lambda row: (row['area'], row['name']))[:10]:
                self.stdout.write(
                    f'  id={item["sensor_id"]} area={item["area"]!r} '
                    f'name={item["name"]!r} level={item["level"]} road={item["road"]}C'
                )
            if len(grouped[status]) > 10:
                self.stdout.write(f'  ... and {len(grouped[status]) - 10} more')

        if preferences.exists():
            self.stdout.write('\nSensors matching registered preferences (current status):')
            for pref in preferences:
                if not pref.notifications_enabled:
                    continue
                matched = []
                for reading in readings:
                    sensor = reading.sensor
                    if not self._matches_area_filter(sensor, area):
                        continue
                    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
                    level = evaluate_ice_warning(reading.road_temperature, dew_point, reading.humidity)
                    alert_status = alert_status_for_level(level)
                    if matches_subscription(pref, sensor) and matches_severity_filter(
                        pref.severity_filter,
                        alert_status,
                    ):
                        matched.append(f'{sensor.id}:{alert_status}')
                self.stdout.write(
                    f'  user_id={pref.user_id}: {", ".join(matched) if matched else "(none right now)"}'
                )

    def _resolve_sensor(self, sensor_id):
        if sensor_id:
            sensor = Sensor.objects.filter(id=sensor_id, active=True).first()
            if not sensor:
                raise CommandError(f'Sensor id={sensor_id} not found.')
            return sensor

        sensor = Sensor.objects.filter(active=True).select_related('municipality').first()
        if not sensor:
            sensor = self._ensure_demo_sensor()
        return sensor

    def _ensure_demo_sensor(self):
        municipality, _ = Municipality.objects.get_or_create(
            name='Hof',
            defaults={
                'geo_boundary': {
                    'type': 'Polygon',
                    'coordinates': [[[11.9, 50.28], [11.98, 50.28], [11.98, 50.34], [11.9, 50.28]]],
                }
            },
        )
        sensor, _ = Sensor.objects.get_or_create(
            external_id='PUSH-TEST-001',
            defaults={
                'name': 'Push Test Sensor Hof',
                'display_name': 'Push Test Sensor Hof',
                'municipality': municipality,
                'latitude': 50.31,
                'longitude': 11.92,
                'sensor_type': Sensor.TYPE_STANDARD,
                'active': True,
            },
        )
        return sensor

    def _create_reading(self, sensor, preset, timestamp):
        return SensorReading.objects.create(
            sensor=sensor,
            timestamp=timestamp,
            device_name=sensor.device_name or sensor.name,
            air_temperature=preset['air_temperature'],
            road_temperature=preset['road_temperature'],
            humidity=preset['humidity'],
            latitude=sensor.latitude,
            longitude=sensor.longitude,
        )

    def _simulate(self, options):
        level = options['simulate']
        sensor = self._resolve_sensor(options['sensor_id'])
        if options['prepare_user']:
            self._prepare_user_preference(options['prepare_user'], sensor, level)

        now = timezone.now()
        preset = READING_PRESETS[level]

        baseline = self._create_reading(
            sensor,
            READING_PRESETS[ICE_WARNING_NONE],
            now - timedelta(minutes=20),
        )
        warning = self._create_reading(
            sensor,
            preset,
            now,
        )

        dew_point = calculate_dew_point(warning.air_temperature, warning.humidity)
        computed_level = evaluate_ice_warning(
            warning.road_temperature,
            dew_point,
            warning.humidity,
        )
        alert_status = alert_status_for_level(computed_level)

        result = notify_sensor_ice_warning(sensor, warning, force=True)
        self.stdout.write(
            self.style.SUCCESS(
                f'Simulated {level} for sensor_id={sensor.id} ({sensor.name}). '
                f'baseline_reading_id={baseline.id}, warning_reading_id={warning.id}'
            )
        )
        self.stdout.write(
            f'Computed level={computed_level} alert_status={alert_status} '
            f'(road={warning.road_temperature}, dew={dew_point}, humidity={warning.humidity})'
        )
        self.stdout.write(
            f"Push result: notified={result['notified']} "
            f"level={result['new_level']} "
            f"users={result.get('matched_users', 0)} sent={result['sent_count']} "
            f"failed={result['failed_count']}"
        )
        if result['sent_count'] == 0:
            self._print_push_diagnostics(sensor, alert_status)

    def _prepare_user_preference(self, user_id, sensor, level):
        municipality_name = sensor.municipality.name if sensor.municipality else 'Hof'
        severity_filter = AlertPreference.SEVERITY_ORANGE
        if level == ICE_WARNING_ACUTE_ICE:
            severity_filter = AlertPreference.SEVERITY_RED

        preference, _ = AlertPreference.objects.update_or_create(
            user_id=user_id,
            defaults={
                'severity_filter': severity_filter,
                'notifications_enabled': True,
                'selected_municipality': municipality_name,
                'selected_sensor_ids': [sensor.id],
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Prepared preferences for user_id={user_id}: '
                f'filter={preference.severity_filter}, municipality={preference.selected_municipality!r}, '
                f'sensors={preference.selected_sensor_ids}'
            )
        )

    def _print_push_diagnostics(self, sensor, alert_status):
        token_count = PushToken.objects.count()
        if token_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    'No push tokens registered. The app must call POST /api/v1/push-tokens/ first.'
                )
            )
            return

        municipality_name = sensor.municipality.name if sensor.municipality else ''
        operator_name = (sensor.operator_name or '').strip()
        self.stdout.write(self.style.WARNING('No push sent. Diagnostics:'))
        self.stdout.write(f'  registered push tokens: {token_count}')
        self.stdout.write(
            f'  sensor_municipality={municipality_name!r}, sensor_operator={operator_name!r}'
        )

        preferences = AlertPreference.objects.filter(notifications_enabled=True)
        if not preferences.exists():
            self.stdout.write('  no enabled alert preferences found')
            return

        for preference in preferences:
            tokens_for_user = PushToken.objects.filter(user_id=preference.user_id).count()
            severity_ok = matches_severity_filter(preference.severity_filter, alert_status)
            subscription_ok = matches_subscription(preference, sensor)
            self.stdout.write(
                f'  user_id={preference.user_id}: tokens={tokens_for_user}, '
                f'filter={preference.severity_filter}, severity_ok={severity_ok}, '
                f'municipality={preference.selected_municipality!r}, '
                f'sensors={preference.selected_sensor_ids}, subscription_ok={subscription_ok}'
            )

        matched = find_subscribed_push_tokens(sensor, alert_status)
        self.stdout.write(f'  tokens that should match now: {len(matched)}')
        self.stdout.write(
            self.style.WARNING(
                'Tip: use --prepare-user <user_id> or --broadcast red for a direct test push.'
            )
        )

    def _broadcast(self, options):
        sensor = self._resolve_sensor(options['sensor_id']) if options['sensor_id'] else None
        colors = ['green', 'yellow', 'orange', 'red'] if options['all_colors'] else [options['broadcast']]

        for alert_status in colors:
            result = send_broadcast_test_pushes(
                alert_status=alert_status,
                user_id=options['user_id'],
                sensor=sensor,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Broadcast {alert_status}: matched={result['matched_tokens']} "
                    f"sent={result['sent_count']} failed={result['failed_count']}"
                )
            )
            if result['matched_tokens'] == 0:
                self.stdout.write(
                    self.style.WARNING(
                        'No push tokens found. Open the app and register via POST /api/v1/push-tokens/.'
                    )
                )
