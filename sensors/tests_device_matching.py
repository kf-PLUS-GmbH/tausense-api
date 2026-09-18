from django.test import TestCase

from sensors.models import Sensor
from sensors.services.device_matching import find_sensor_by_webhook_device_name


class DeviceMatchingTests(TestCase):
    def test_short_webhook_name_matches_long_import_name(self):
        Sensor.objects.create(
            name='Münchberg 1',
            device_name='MUB-TPK-0001-N50.22764-E11.76708',
            sensor_type=Sensor.TYPE_STANDARD,
            operator_name='Münchberg',
        )
        match = find_sensor_by_webhook_device_name('MUB-TPK-0001')
        self.assertIsNotNone(match)
        self.assertEqual(match.device_name, 'MUB-TPK-0001-N50.22764-E11.76708')

    def test_exact_match_still_works(self):
        Sensor.objects.create(
            name='Test',
            device_name='KOE-TPK-0005-N50.37151-E11.83813',
            sensor_type=Sensor.TYPE_STANDARD,
        )
        match = find_sensor_by_webhook_device_name('KOE-TPK-0005-N50.37151-E11.83813')
        self.assertEqual(match.device_name, 'KOE-TPK-0005-N50.37151-E11.83813')
