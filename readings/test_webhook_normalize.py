from django.test import SimpleTestCase

from readings.services.webhook_normalize import (
    normalize_incoming_webhook_payload,
    should_ignore_webhook_event,
)


class WebhookNormalizeTests(SimpleTestCase):
    def test_chirpstack_uplink_flattened(self):
        raw = {
            'time': '2026-06-03T09:10:06.316Z',
            'deviceInfo': {
                'devEui': '70b3d57ba000638d',
                'deviceName': 'MUB-TPK-0001-N50.22764-E11.76708',
            },
            'object': {
                'air_temperature_radiation_shield': 12.84,
                'air_humidity_radiation_shield': 83.77,
                'surface_temperature': 24.8,
            },
            'rxInfo': [
                {'location': {'latitude': 99.0, 'longitude': 88.0}},
            ],
        }
        flat = normalize_incoming_webhook_payload(raw)

        self.assertEqual(flat['deviceEui'], '70b3d57ba000638d')
        self.assertEqual(flat['deviceName'], 'MUB-TPK-0001-N50.22764-E11.76708')
        self.assertEqual(flat['timestamp'], '2026-06-03T09:10:06.316Z')
        self.assertEqual(flat['air_temperature_radiation_shield'], 12.84)
        self.assertEqual(flat['surface_temperature'], 24.8)
        self.assertEqual(flat['lat'], 50.22764)
        self.assertEqual(flat['lon'], 11.76708)

    def test_flat_payload_unchanged(self):
        raw = {
            'deviceEui': 'ABC',
            'timestamp': '2026-01-01T00:00:00Z',
            'air_temperature': 1.0,
            'air_humidity': 80.0,
            'surface_temperature': 0.5,
        }
        flat = normalize_incoming_webhook_payload(raw)
        self.assertEqual(flat['deviceEui'], 'ABC')

    def test_ignore_non_up_events(self):
        self.assertFalse(should_ignore_webhook_event('up'))
        self.assertTrue(should_ignore_webhook_event('join'))
        self.assertFalse(should_ignore_webhook_event(None))
