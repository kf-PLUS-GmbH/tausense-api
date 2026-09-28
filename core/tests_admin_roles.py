from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from core.roles import GROUP_ADMIN, GROUP_VIEWER, ensure_admin_groups
from sensors.models import Sensor


class AdminRoleTests(TestCase):
    def setUp(self):
        ensure_admin_groups()
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='test-pass-123',
            is_staff=True,
        )
        self.admin_user.groups.add(Group.objects.get(name=GROUP_ADMIN))

        self.viewer_user = User.objects.create_user(
            username='viewer_user',
            password='test-pass-123',
            is_staff=True,
        )
        self.viewer_user.groups.add(Group.objects.get(name=GROUP_VIEWER))

        self.sensor = Sensor.objects.create(
            name='Test Sensor',
            device_name='TEST-001',
            external_id='eui-test-001',
            sensor_type=Sensor.TYPE_STANDARD,
        )

    def test_viewer_cannot_add_sensor(self):
        client = Client()
        client.force_login(self.viewer_user)
        url = reverse('admin:sensors_sensor_add')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_open_sensor_add(self):
        client = Client()
        client.force_login(self.admin_user)
        url = reverse('admin:sensors_sensor_add')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_viewer_can_list_sensors(self):
        client = Client()
        client.force_login(self.viewer_user)
        url = reverse('admin:sensors_sensor_changelist')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Sensor')

    def test_viewer_cannot_delete_sensor(self):
        client = Client()
        client.force_login(self.viewer_user)
        url = reverse('admin:sensors_sensor_delete', args=[self.sensor.pk])
        response = client.post(url, {'post': 'yes'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Sensor.objects.filter(pk=self.sensor.pk).exists())
