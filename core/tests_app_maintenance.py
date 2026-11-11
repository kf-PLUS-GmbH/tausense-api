from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.app_maintenance import (
    STATE_ACTIVE,
    STATE_ENDED,
    STATE_INACTIVE,
    STATE_SCHEDULED,
    resolve_app_maintenance,
)
from core.models import AppMaintenanceSettings


class AppMaintenanceResolveTests(TestCase):
    def setUp(self):
        AppMaintenanceSettings.objects.all().delete()
        self.settings = AppMaintenanceSettings.load()

    def test_disabled(self):
        self.settings.enabled = False
        self.settings.save()
        payload = resolve_app_maintenance(self.settings)
        self.assertEqual(payload['state'], STATE_INACTIVE)
        self.assertFalse(payload['active'])

    def test_active_immediately(self):
        self.settings.enabled = True
        self.settings.message = 'Kurz Wartung.'
        self.settings.save()
        payload = resolve_app_maintenance(self.settings)
        self.assertEqual(payload['state'], STATE_ACTIVE)
        self.assertTrue(payload['active'])

    def test_scheduled(self):
        self.settings.enabled = True
        self.settings.starts_at = timezone.now() + timezone.timedelta(hours=2)
        self.settings.save()
        payload = resolve_app_maintenance(self.settings)
        self.assertEqual(payload['state'], STATE_SCHEDULED)
        self.assertFalse(payload['active'])

    def test_ended(self):
        self.settings.enabled = True
        self.settings.ends_at = timezone.now() - timezone.timedelta(minutes=1)
        self.settings.save()
        payload = resolve_app_maintenance(self.settings)
        self.assertEqual(payload['state'], STATE_ENDED)
        self.assertFalse(payload['active'])


class AppMaintenanceApiTests(TestCase):
    def test_get_endpoint(self):
        client = APIClient()
        response = client.get('/api/v1/system/app-maintenance/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('app_maintenance', response.json())
        self.assertIn('active', response.json()['app_maintenance'])
