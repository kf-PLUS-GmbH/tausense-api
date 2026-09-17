from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from readings.models import SensorReading
from sensors.models import Sensor

WEBHOOK_PAYLOAD = {
    'deviceEui': '70B3D57BA0009999',
    'deviceName': 'WEBHOOK-AUTH-TEST',
    'timestamp': '2026-06-03T09:10:06.316Z',
    'air_temperature_radiation_shield': 12.0,
    'air_humidity_radiation_shield': 80.0,
}


class ReadingHistoryAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sensor = Sensor.objects.create(
            name='Test Sensor',
            display_name='Test Display',
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
        )
        now = timezone.now()
        self.reading_old = SensorReading.objects.create(
            sensor=self.sensor,
            timestamp=now - timedelta(days=3),
            air_temperature=1.0,
            road_temperature=0.5,
            humidity=85.0,
        )
        self.reading_new = SensorReading.objects.create(
            sensor=self.sensor,
            timestamp=now - timedelta(days=1),
            air_temperature=2.0,
            road_temperature=1.0,
            humidity=80.0,
        )

    def test_history_requires_sensor(self):
        response = self.client.get('/api/v1/readings/history/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], 'sensor is required.')

    def test_history_returns_points_ordered_ascending(self):
        response = self.client.get(
            '/api/v1/readings/history/',
            {'sensor': self.sensor.id, 'days': 7},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload['sensor_id'], self.sensor.id)
        self.assertEqual(payload['sensor_name'], 'Test Display')
        self.assertEqual(payload['days'], 7)
        self.assertEqual(payload['count'], 2)
        self.assertEqual(len(payload['points']), 2)
        self.assertLess(payload['points'][0]['timestamp'], payload['points'][1]['timestamp'])
        self.assertIn('air_temperature', payload['points'][0])
        self.assertIn('road_temperature', payload['points'][0])
        self.assertIn('humidity', payload['points'][0])
        self.assertIn('dew_point', payload['points'][0])
        self.assertIn('ice_warning_level', payload['points'][0])
        self.assertIn('alert_status', payload['points'][0])

    def test_history_rejects_days_over_14(self):
        response = self.client.get(
            '/api/v1/readings/history/',
            {'sensor': self.sensor.id, 'days': 15},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['field'], 'days')

    def test_history_rejects_range_over_14_days(self):
        now = timezone.now()
        response = self.client.get(
            '/api/v1/readings/history/',
            {
                'sensor': self.sensor.id,
                'from': (now - timedelta(days=20)).isoformat(),
                'to': now.isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['field'], 'to')

    def test_history_unknown_sensor(self):
        response = self.client.get(
            '/api/v1/readings/history/',
            {'sensor': 99999, 'days': 7},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['field'], 'sensor')


@override_settings(WEBHOOK_SECRET='hook-secret')
class WebhookAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/webhook/'

    def test_webhook_rejects_missing_authorization(self):
        response = self.client.post(self.url, WEBHOOK_PAYLOAD, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(SensorReading.objects.count(), 0)

    def test_webhook_rejects_wrong_bearer_token(self):
        response = self.client.post(
            self.url,
            WEBHOOK_PAYLOAD,
            format='json',
            HTTP_AUTHORIZATION='Bearer wrong',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(SensorReading.objects.count(), 0)

    def test_webhook_accepts_valid_bearer_token(self):
        response = self.client.post(
            self.url,
            WEBHOOK_PAYLOAD,
            format='json',
            HTTP_AUTHORIZATION='Bearer hook-secret',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SensorReading.objects.count(), 1)


@override_settings(WEBHOOK_SECRET='')
class WebhookAuthOptionalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/webhook/'

    def test_webhook_allows_request_when_secret_not_configured(self):
        response = self.client.post(self.url, WEBHOOK_PAYLOAD, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SensorReading.objects.count(), 1)
