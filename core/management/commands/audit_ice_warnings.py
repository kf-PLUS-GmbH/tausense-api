from django.core.management.base import BaseCommand

from core.ice_warning import (
    ICE_WARNING_LABELS,
    alert_status_for_level,
    evaluate_ice_warning,
    precipitation_detected,
)
from core.ice_warning_state import update_sensor_ice_warning_from_reading
from readings.selectors import latest_readings_with_previous
from core.utils import calculate_dew_point
class Command(BaseCommand):
    help = (
        'Compare instantaneous ice triggers with active stored levels shown on the map. '
        'Useful when markers stay red/yellow although current T_road looks harmless.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--mismatch-only',
            action='store_true',
            help='Only list sensors where instant trigger != active map level.',
        )
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        mismatch_only = options['mismatch_only']
        limit = options['limit']

        rows = []
        for reading in latest_readings_with_previous().order_by(
            'sensor_id',
            '-timestamp',
            '-id',
        ):
            if any(r['sensor_id'] == reading.sensor_id for r in rows):
                continue
            sensor = reading.sensor
            dew = calculate_dew_point(reading.air_temperature, reading.humidity)
            precip = precipitation_detected(reading.raw_data)
            instant = evaluate_ice_warning(
                reading.road_temperature,
                dew,
                reading.humidity,
                precipitation=precip,
            )
            stored_before = sensor.ice_warning_level
            active = update_sensor_ice_warning_from_reading(sensor, reading)
            if mismatch_only and instant == active:
                continue
            rows.append(
                {
                    'sensor_id': sensor.id,
                    'name': sensor.display_name or sensor.name,
                    'road': reading.road_temperature,
                    'air': reading.air_temperature,
                    'rh': reading.humidity,
                    'dew': round(dew, 2),
                    'precip': precip,
                    'stored_before': stored_before,
                    'instant': instant,
                    'active': active,
                    'alert': alert_status_for_level(active),
                    'since': sensor.ice_warning_level_since,
                },
            )
            if len(rows) >= limit:
                break

        if not rows:
            self.stdout.write(self.style.SUCCESS('No rows to show.'))
            return

        for row in rows:
            self.stdout.write(
                f"#{row['sensor_id']} {row['name']}\n"
                f"  T_road={row['road']}°C  T_air={row['air']}°C  RH={row['rh']}%  "
                f"Td={row['dew']}°C  precip={row['precip']}\n"
                f"  instant={row['instant']} ({ICE_WARNING_LABELS[row['instant']]})\n"
                f"  active(map)={row['active']} ({ICE_WARNING_LABELS[row['active']]} → {row['alert']})\n"
                f"  level_since={row['since']}\n",
            )
