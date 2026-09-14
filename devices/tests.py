from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient

from core.ice_warning import (
    ICE_WARNING_ACUTE_ICE,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
)
from devices.models import AlertPreference, PushDigestState, PushToken
from devices.services.digest import build_warning_digest, collect_warning_sensors
from devices.services.push import send_push_notification
from devices.services.subscriptions import (
    _should_send_digest,
    find_subscribed_push_tokens,
    matches_severity_filter,
    matches_subscription,
    notify_sensor_ice_warning,
)
from municipalities.models import Municipality
from readings.models import SensorReading
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
    def test_notify_on_first_warning(self):
        self.assertTrue(_should_send_digest(state=None, worst_severity=2, sensor_count=1))

    def test_notify_on_escalation(self):
        state = PushDigestState(
            last_worst_severity=1,
            last_sensor_count=1,
            last_sent_at=timezone.now(),
        )
        self.assertTrue(_should_send_digest(state=state, worst_severity=3, sensor_count=1))

    def test_skip_when_no_warning(self):
        self.assertFalse(_should_send_digest(state=None, worst_severity=0, sensor_count=0))

    def test_skip_when_same_level_before_reminder(self):
        state = PushDigestState(
            last_worst_severity=2,
            last_sensor_count=2,
            last_sent_at=timezone.now(),
        )
        self.assertFalse(_should_send_digest(state=state, worst_severity=2, sensor_count=2))

    def test_notify_when_same_level_after_reminder(self):
        state = PushDigestState(
            last_worst_severity=2,
            last_sensor_count=2,
            last_sent_at=timezone.now() - timedelta(minutes=31),
        )
        self.assertTrue(_should_send_digest(state=state, worst_severity=2, sensor_count=2))

    def test_notify_when_sensor_count_increases(self):
        state = PushDigestState(
            last_worst_severity=2,
            last_sensor_count=1,
            last_sent_at=timezone.now(),
        )
        self.assertTrue(_should_send_digest(state=state, worst_severity=2, sensor_count=2))


class PushReminderFlowTests(TestCase):
    def setUp(self):
        self.sensor = Sensor.objects.create(
            name='Reminder Sensor',
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='REM-001',
        )
        AlertPreference.objects.create(
            user_id='user-reminder',
            severity_filter='orange',
            notifications_enabled=True,
            selected_sensor_ids=[self.sensor.id],
        )
        PushToken.objects.create(
            user_id='user-reminder',
            fcm_token='token-reminder',
            platform='android',
        )

    def _reading(self, road_temperature: float, humidity: float = 92.0, air_temperature: float = 1.0):
        return SensorReading.objects.create(
            sensor=self.sensor,
            timestamp=timezone.now(),
            air_temperature=air_temperature,
            road_temperature=road_temperature,
            humidity=humidity,
        )

    @patch('devices.services.subscriptions.send_digest_push_notification')
    def test_first_orange_warning_sends_push(self, mock_send):
        mock_send.return_value = MagicMock(success=True)

        result = notify_sensor_ice_warning(self.sensor, self._reading(road_temperature=1.0))

        self.assertTrue(result['notified'])
        mock_send.assert_called_once()
        digest = mock_send.call_args.kwargs['digest']
        self.assertEqual(digest.type, 'digest')
        self.assertEqual(digest.sensor_count, 1)

    @patch('devices.services.subscriptions.send_digest_push_notification')
    def test_same_orange_level_skips_before_reminder(self, mock_send):
        mock_send.return_value = MagicMock(success=True)
        notify_sensor_ice_warning(self.sensor, self._reading(road_temperature=1.0))

        result = notify_sensor_ice_warning(self.sensor, self._reading(road_temperature=1.0))

        self.assertFalse(result['notified'])
        self.assertEqual(mock_send.call_count, 1)

    @patch('devices.services.subscriptions.send_digest_push_notification')
    def test_same_orange_level_reminds_after_30_minutes(self, mock_send):
        mock_send.return_value = MagicMock(success=True)
        reading = self._reading(road_temperature=1.0)
        notify_sensor_ice_warning(self.sensor, reading)

        PushDigestState.objects.filter(user_id='user-reminder').update(
            last_sent_at=timezone.now() - timedelta(minutes=31),
        )

        result = notify_sensor_ice_warning(self.sensor, self._reading(road_temperature=1.0))

        self.assertTrue(result['notified'])
        self.assertEqual(mock_send.call_count, 2)

    @patch('devices.services.subscriptions.send_digest_push_notification')
    def test_clear_warning_resets_state(self, mock_send):
        mock_send.return_value = MagicMock(success=True)
        notify_sensor_ice_warning(self.sensor, self._reading(road_temperature=1.0))
        self.assertEqual(PushDigestState.objects.count(), 1)

        notify_sensor_ice_warning(
            self.sensor,
            self._reading(road_temperature=5.0, humidity=50.0, air_temperature=5.0),
        )

        self.assertEqual(PushDigestState.objects.count(), 0)


class MunicipalityDigestPushTests(TestCase):
    def setUp(self):
        self.sensor_one = Sensor.objects.create(
            name='Stammbach 1',
            operator_name='Stammbach',
            latitude=50.3,
            longitude=11.9,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='STB-001',
        )
        self.sensor_two = Sensor.objects.create(
            name='Stammbach 2',
            operator_name='Stammbach',
            latitude=50.31,
            longitude=11.91,
            sensor_type=Sensor.TYPE_STANDARD,
            active=True,
            external_id='STB-002',
        )
        AlertPreference.objects.create(
            user_id='user-digest',
            severity_filter='orange',
            notifications_enabled=True,
            selected_municipality='Stammbach',
        )
        PushToken.objects.create(
            user_id='user-digest',
            fcm_token='token-digest',
            platform='android',
        )

    def _reading(self, sensor, road_temperature: float, humidity: float = 92.0, air_temperature: float = 1.0):
        return SensorReading.objects.create(
            sensor=sensor,
            timestamp=timezone.now(),
            air_temperature=air_temperature,
            road_temperature=road_temperature,
            humidity=humidity,
        )

    @patch('devices.services.subscriptions.send_digest_push_notification')
    def test_municipality_digest_groups_multiple_sensors(self, mock_send):
        mock_send.return_value = MagicMock(success=True)
        self._reading(self.sensor_one, road_temperature=1.0)
        self._reading(self.sensor_two, road_temperature=1.0)

        result = notify_sensor_ice_warning(self.sensor_two, self._reading(self.sensor_two, road_temperature=1.0))

        self.assertTrue(result['notified'])
        mock_send.assert_called_once()
        digest = mock_send.call_args.kwargs['digest']
        self.assertEqual(digest.sensor_count, 2)
        self.assertEqual(set(digest.sensor_ids), {self.sensor_one.id, self.sensor_two.id})
        self.assertIn('2 Standorten', digest.body)

    def test_build_digest_for_single_sensor(self):
        preference = AlertPreference.objects.get(user_id='user-digest')
        self._reading(self.sensor_one, road_temperature=1.0)
        warnings = collect_warning_sensors(preference)
        digest = build_warning_digest(preference, warnings)

        self.assertEqual(digest.sensor_count, 1)
        self.assertEqual(digest.title, 'Warnung: Stammbach 1')


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
