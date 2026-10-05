import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from analytics.merge import merge_usage_days
from analytics.models import UsageAnalyticsInstallation


class UsageAnalyticsMergeTests(TestCase):
    def test_merge_same_day_adds_counters(self):
        existing = {
            '2026-04-11': {
                'sessions': 1,
                'screens': {'map': 2},
                'last_active_at': '2026-04-11T08:00:00.000Z',
            },
        }
        incoming = {
            '2026-04-11': {
                'sessions': 2,
                'screens': {'map': 3, 'dashboard': 1},
                'last_active_at': '2026-04-11T09:30:00.000Z',
            },
        }
        merged = merge_usage_days(existing, incoming)
        day = merged['2026-04-11']
        self.assertEqual(day['sessions'], 3)
        self.assertEqual(day['screens']['map'], 5)
        self.assertEqual(day['screens']['dashboard'], 1)
        self.assertEqual(day['last_active_at'], '2026-04-11T09:30:00.000Z')


class UsageAnalyticsUploadAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.installation_id = str(uuid.uuid4())

    def _sample_payload(self, **overrides):
        payload = {
            'schema_version': 1,
            'installation_id': self.installation_id,
            'updated_at': '2026-04-11T09:41:00.000Z',
            'days': {
                '2026-04-11': {
                    'sessions': 2,
                    'screens': {'map': 5},
                    'actions': {'location_button': 1},
                },
            },
        }
        payload.update(overrides)
        return payload

    def test_upload_creates_installation(self):
        response = self.client.post(
            '/api/v1/analytics/usage/',
            self._sample_payload(),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        record = UsageAnalyticsInstallation.objects.get(
            installation_id=self.installation_id,
        )
        self.assertEqual(record.days['2026-04-11']['sessions'], 2)
        self.assertEqual(response.data['day_count'], 1)

    def test_upload_merges_existing_day(self):
        self.client.post(
            '/api/v1/analytics/usage/',
            self._sample_payload(),
            format='json',
        )
        response = self.client.post(
            '/api/v1/analytics/usage/',
            self._sample_payload(
                days={
                    '2026-04-11': {
                        'sessions': 1,
                        'screens': {'map': 2},
                    },
                },
            ),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        record = UsageAnalyticsInstallation.objects.get(
            installation_id=self.installation_id,
        )
        self.assertEqual(record.days['2026-04-11']['sessions'], 3)
        self.assertEqual(record.days['2026-04-11']['screens']['map'], 7)

    def test_rejects_unsupported_schema(self):
        response = self.client.post(
            '/api/v1/analytics/usage/',
            self._sample_payload(schema_version=2),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
