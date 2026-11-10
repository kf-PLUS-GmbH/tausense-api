from django.test import TestCase, override_settings
from django.utils import timezone

from core.map_display import resolve_map_measurement_context
from core.reading_plausibility import is_reading_plausible
from core.services import dashboard_map_data
from readings.models import SensorReading
from municipalities.models import Municipality
from sensors.models import Sensor


class ReadingPlausibilityTests(TestCase):
    def test_default_road_min_minus_50(self):
        self.assertFalse(is_reading_plausible(road_temperature=-100, air_temperature=5, humidity=50))
        self.assertTrue(is_reading_plausible(road_temperature=-50, air_temperature=5, humidity=50))

    @override_settings(
        READING_PLAUSIBILITY={
            'road_temp_min': -40.0,
            'road_temp_max': 60.0,
            'air_temp_min': -50.0,
            'air_temp_max': 50.0,
            'humidity_min': 0.0,
            'humidity_max': 100.0,
        },
    )
    def test_env_override_via_settings(self):
        self.assertFalse(is_reading_plausible(road_temperature=-45, air_temperature=5, humidity=50))


class MapMeasurementContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.municipality = Municipality.objects.create(name='Hof')
        cls.sensor = Sensor.objects.create(
            name='Test',
            external_id='ext-map-plaus',
            municipality=cls.municipality,
            latitude=50.0,
            longitude=11.0,
            ice_warning_level='possible_slip',
        )
        now = timezone.now()
        cls.good = SensorReading.objects.create(
            sensor=cls.sensor,
            timestamp=now,
            air_temperature=2.0,
            road_temperature=1.0,
            humidity=80.0,
            is_plausible=True,
        )
        cls.bad = SensorReading.objects.create(
            sensor=cls.sensor,
            timestamp=now + timezone.timedelta(minutes=5),
            air_temperature=2.0,
            road_temperature=-100.0,
            humidity=80.0,
            is_plausible=False,
        )

    def test_ok_omits_display_reading(self):
        ctx = resolve_map_measurement_context(
            self.sensor,
            self.good,
            self.good,
            previous_air_for_display=None,
        )
        self.assertEqual(ctx['measurement_status'], 'ok')
        self.assertIsNotNone(ctx['latest_reading'])
        self.assertIsNone(ctx['display_reading'])

    def test_unreliable_uses_last_plausible_display(self):
        ctx = resolve_map_measurement_context(
            self.sensor,
            self.bad,
            self.good,
            previous_air_for_display=None,
        )
        self.assertEqual(ctx['measurement_status'], 'unreliable')
        self.assertEqual(ctx['display_reading']['road_temperature'], 1.0)
        self.assertTrue(ctx['display_reading']['is_stale'])
        self.assertFalse(ctx['latest_reading']['is_plausible'])

    def test_maintenance_gray_alert(self):
        self.sensor.maintenance_mode = True
        self.sensor.save(update_fields=['maintenance_mode'])
        ctx = resolve_map_measurement_context(
            self.sensor,
            self.bad,
            self.good,
            previous_air_for_display=None,
        )
        self.assertEqual(ctx['measurement_status'], 'maintenance')
        self.assertEqual(ctx['alert_status'], 'gray')

    def test_dashboard_map_data_exposes_new_fields(self):
        rows = dashboard_map_data()
        row = next(r for r in rows if r['sensor_id'] == self.sensor.id)
        self.assertIn('measurement_status', row)
        self.assertIn('display_reading', row)
        self.assertEqual(row['measurement_status'], 'unreliable')
