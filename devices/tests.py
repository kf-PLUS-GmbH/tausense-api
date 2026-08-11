from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.ice_warning import ICE_WARNING_ACUTE_ICE, ICE_WARNING_NONE, ICE_WARNING_POSSIBLE_SLIP
from devices.models import AlertPreference, PushToken
from devices.services.push import send_push_notification
from devices.services.subscriptions import (
    _should_notify,
    find_subscribed_push_tokens,
    matches_severity_filter,
    matches_subscription,
)
from municipalities.models import Municipality
from sensors.models import Sensor


class AlertPreferencesAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_save_preferences_with_user_id_in_body(self):
        response = self.client.post(
            '/api/v1/alerts/preferences/',
            {
                'user_id': 'user-1',
                'severity_filter': 'orange',
                'notifications_enabled': True,
                'selected_municipality': 'Hof',
                'selected_sensor_ids': [1, 2],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = AlertPreference.objects.get(user_id='user-1')
        self.assertEqual(preference.severity_filter, 'orange')
        self.assertEqual(preference.selected_sensor_ids, [1, 2])

    def test_save_preferences_with_user_id_header(self):
        response = self.client.post(
            '/api/v1/alerts/preferences/',
            {
                'severity_filter': 'red',
                'notifications_enabled': False,
                'selected_municipality': None,
                'selected_sensor_ids': [],
            },
            format='json',
            HTTP_X_USER_ID='header-user',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference = AlertPreference.objects.get(user_id='header-user')
        self.assertEqual(preference.severity_filter, 'red')
        self.assertFalse(preference.notifications_enabled)


class PushTokenAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_push_token(self):
        response = self.client.post(
            '/api/v1/push-tokens/',
            {
                'user_id': 'user-1',
                'fcm_token': 'token-abc',
                'platform': 'android',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PushToken.objects.filter(fcm_token='token-abc').exists())

    def test_update_existing_push_token(self):
        PushToken.objects.create(
            user_id='old-user',
            fcm_token='token-abc',
            platform='ios',
        )

        response = self.client.post(
            '/api/v1/push-tokens/',
            {
                'user_id': 'new-user',
                'fcm_token': 'token-abc',
                'platform': 'android',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = PushToken.objects.get(fcm_token='token-abc')
        self.assertEqual(token.user_id, 'new-user')
        self.assertEqual(token.platform, 'android')


class SubscriptionMatchingTests(TestCase):
    def setUp(self):
        self.municipality = Municipality.objects.create(
            name='Hof',
            geo_boundary={'type': 'Polygon', 'coordinates': []},
        )
        self.sensor = Sensor.objects.create(
            name='Sensor Hof',
            municipality=self.municipality,
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='HOF-001',
        )

    def test_match_by_sensor_id(self):
        AlertPreference.objects.create(
            user_id='u1',
            severity_filter='orange',
            notifications_enabled=True,
            selected_sensor_ids=[self.sensor.id],
        )
        PushToken.objects.create(user_id='u1', fcm_token='token-1', platform='android')
        matched = find_subscribed_push_tokens(self.sensor, 'orange')
        self.assertEqual(len(matched), 1)

    def test_match_by_municipality(self):
        AlertPreference.objects.create(
            user_id='u2',
            severity_filter='orange',
            notifications_enabled=True,
            selected_municipality='Hof',
        )
        PushToken.objects.create(user_id='u2', fcm_token='token-2', platform='android')
        matched = find_subscribed_push_tokens(self.sensor, 'red')
        self.assertEqual(len(matched), 1)

    def test_red_filter_skips_orange_alert(self):
        AlertPreference.objects.create(
            user_id='u3',
            severity_filter='red',
            notifications_enabled=True,
            selected_municipality='Hof',
        )
        PushToken.objects.create(user_id='u3', fcm_token='token-3', platform='android')
        matched = find_subscribed_push_tokens(self.sensor, 'orange')
        self.assertEqual(len(matched), 0)

    def test_disabled_notifications_are_skipped(self):
        AlertPreference.objects.create(
            user_id='u4',
            severity_filter='orange',
            notifications_enabled=False,
            selected_municipality='Hof',
        )
        PushToken.objects.create(user_id='u4', fcm_token='token-4', platform='android')
        matched = find_subscribed_push_tokens(self.sensor, 'red')
        self.assertEqual(len(matched), 0)


    def test_match_by_operator_name(self):
        sensor = Sensor.objects.create(
            name='Stammbach Sensor',
            operator_name='Stammbach',
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='STB-003',
        )
        AlertPreference.objects.create(
            user_id='u5',
            severity_filter='orange',
            notifications_enabled=True,
            selected_municipality='Stammbach',
        )
        PushToken.objects.create(user_id='u5', fcm_token='token-5', platform='android')
        matched = find_subscribed_push_tokens(sensor, 'orange')
        self.assertEqual(len(matched), 1)


class SeverityFilterTests(TestCase):
    def test_orange_includes_orange_and_red(self):
        self.assertTrue(matches_severity_filter('orange', 'orange'))
        self.assertTrue(matches_severity_filter('orange', 'red'))
        self.assertFalse(matches_severity_filter('orange', 'yellow'))

    def test_red_only_includes_red(self):
        self.assertTrue(matches_severity_filter('red', 'red'))
        self.assertFalse(matches_severity_filter('red', 'orange'))


class PreferenceSubscriptionTests(TestCase):
    def setUp(self):
        self.municipality = Municipality.objects.create(
            name='Hof',
            geo_boundary={'type': 'Polygon', 'coordinates': []},
        )
        self.sensor = Sensor.objects.create(
            name='Sensor Hof',
            municipality=self.municipality,
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='HOF-001',
        )
        self.preference = AlertPreference(
            user_id='u1',
            severity_filter='orange',
            notifications_enabled=True,
            selected_municipality='Hof',
            selected_sensor_ids=[],
        )

    def test_matches_municipality(self):
        self.assertTrue(matches_subscription(self.preference, self.sensor))

    def test_no_match_for_other_municipality(self):
        self.preference.selected_municipality = 'Rehau'
        self.assertFalse(matches_subscription(self.preference, self.sensor))

    def test_matches_operator_name_when_municipality_missing(self):
        sensor = Sensor.objects.create(
            name='Stammbach Sensor',
            operator_name='Stammbach',
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='STB-001',
        )
        preference = AlertPreference(
            user_id='u2',
            severity_filter='orange',
            notifications_enabled=True,
            selected_municipality='Stammbach',
            selected_sensor_ids=[],
        )
        self.assertTrue(matches_subscription(preference, sensor))

    def test_favorites_and_municipality_use_or_logic(self):
        other_sensor = Sensor.objects.create(
            name='Other Sensor',
            operator_name='Stammbach',
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='STB-002',
        )
        preference = AlertPreference(
            user_id='u3',
            severity_filter='orange',
            notifications_enabled=True,
            selected_municipality='Stammbach',
            selected_sensor_ids=[self.sensor.id],
        )
        self.assertTrue(matches_subscription(preference, self.sensor))
        self.assertTrue(matches_subscription(preference, other_sensor))


class IceWarningNotificationDecisionTests(TestCase):
    def test_notify_on_new_warning(self):
        self.assertTrue(_should_notify(ICE_WARNING_NONE, ICE_WARNING_POSSIBLE_SLIP))

    def test_notify_on_escalation(self):
        self.assertTrue(_should_notify(ICE_WARNING_POSSIBLE_SLIP, ICE_WARNING_ACUTE_ICE))

    def test_skip_when_no_warning(self):
        self.assertFalse(_should_notify(ICE_WARNING_POSSIBLE_SLIP, ICE_WARNING_NONE))

    def test_skip_when_same_level(self):
        self.assertFalse(_should_notify(ICE_WARNING_POSSIBLE_SLIP, ICE_WARNING_POSSIBLE_SLIP))


class PushServiceTests(TestCase):
    @patch('devices.services.push.is_firebase_ready', return_value=False)
    def test_push_skipped_when_firebase_not_ready(self, _mock_ready):
        result = send_push_notification(
            fcm_token='token-abc',
            sensor_id=1,
            alert_status='red',
            sensor_name='Test Sensor',
            municipality_name='Hof',
            title='Warnung',
            body='Test',
        )
        self.assertFalse(result.success)
        self.assertIn('not initialized', result.error.lower())

    @patch('firebase_admin.messaging.send', return_value='projects/test/messages/123')
    @patch('firebase_admin.messaging.Message')
    @patch('firebase_admin.messaging.Notification')
    @patch('devices.services.push.is_firebase_ready', return_value=True)
    def test_push_success(self, _mock_ready, _mock_notification, _mock_message, mock_send):
        result = send_push_notification(
            fcm_token='token-abc',
            sensor_id=1,
            alert_status='red',
            sensor_name='Test Sensor',
            municipality_name='Hof',
            title='Warnung',
            body='Test',
        )
        self.assertTrue(result.success)
        self.assertEqual(result.message_id, 'projects/test/messages/123')
        mock_send.assert_called_once()


class TestPushEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch.dict('os.environ', {'TEST_PUSH_ENABLED': 'false', 'TEST_PUSH_SECRET': ''})
    def test_test_push_disabled_by_default(self):
        response = self.client.post(
            '/api/test/push/',
            {
                'device_token': 'token-abc',
                'sensor_id': 1,
                'alert_status': 'red',
                'sensor_name': 'Test',
                'municipality_name': 'Hof',
                'title': 'Test',
                'body': 'Test',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch.dict('os.environ', {'TEST_PUSH_ENABLED': 'true', 'TEST_PUSH_SECRET': ''})
    @patch('devices.views.send_push_notification')
    def test_test_push_enabled(self, mock_send):
        mock_send.return_value = MagicMock(success=True, message_id='msg-1', error=None, token_removed=False)

        response = self.client.post(
            '/api/test/push/',
            {
                'device_token': 'token-abc',
                'sensor_id': 1,
                'alert_status': 'red',
                'sensor_name': 'Test',
                'municipality_name': 'Hof',
                'title': 'Test',
                'body': 'Test',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
