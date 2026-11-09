from django.test import SimpleTestCase

from devices.notification_schedule import (
    is_push_allowed_by_schedule,
    is_within_notification_window,
)


class NotificationScheduleWindowTests(SimpleTestCase):
    def test_same_start_end_is_all_day(self):
        self.assertTrue(
            is_within_notification_window(
                start='03:00',
                end='03:00',
                tz_name='Europe/Berlin',
                now_minutes=2 * 60 + 30,
            ),
        )

    def test_simple_window(self):
        self.assertFalse(
            is_within_notification_window(
                start='10:00',
                end='11:00',
                tz_name='Europe/Berlin',
                now_minutes=9 * 60 + 59,
            ),
        )
        self.assertTrue(
            is_within_notification_window(
                start='10:00',
                end='11:00',
                tz_name='Europe/Berlin',
                now_minutes=10 * 60 + 30,
            ),
        )
        self.assertTrue(
            is_within_notification_window(
                start='10:00',
                end='11:00',
                tz_name='Europe/Berlin',
                now_minutes=11 * 60,
            ),
        )
        self.assertFalse(
            is_within_notification_window(
                start='10:00',
                end='11:00',
                tz_name='Europe/Berlin',
                now_minutes=11 * 60 + 1,
            ),
        )

    def test_overnight_window(self):
        self.assertTrue(
            is_within_notification_window(
                start='22:00',
                end='06:00',
                tz_name='Europe/Berlin',
                now_minutes=23 * 60,
            ),
        )
        self.assertTrue(
            is_within_notification_window(
                start='22:00',
                end='06:00',
                tz_name='Europe/Berlin',
                now_minutes=2 * 60,
            ),
        )
        self.assertFalse(
            is_within_notification_window(
                start='22:00',
                end='06:00',
                tz_name='Europe/Berlin',
                now_minutes=12 * 60,
            ),
        )


class NotificationScheduleDispatchTests(SimpleTestCase):
    def test_disabled_schedule_allows(self):
        self.assertTrue(is_push_allowed_by_schedule({'enabled': False}))

    def test_enabled_within_window(self):
        sch = {
            'enabled': True,
            'start': '10:00',
            'end': '11:00',
            'timezone': 'Europe/Berlin',
        }
        self.assertTrue(is_push_allowed_by_schedule(sch, now_minutes=10 * 60 + 30))

    def test_enabled_outside_window(self):
        sch = {
            'enabled': True,
            'start': '10:00',
            'end': '11:00',
            'timezone': 'Europe/Berlin',
        }
        self.assertFalse(is_push_allowed_by_schedule(sch, now_minutes=8 * 60))
