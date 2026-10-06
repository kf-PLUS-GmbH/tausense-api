from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from core.ice_warning import (
    ICE_WARNING_ACUTE_ICE,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
    alert_status_for_level,
    evaluate_ice_warning,
    transition_ice_warning_level,
)


class _ReadingStub:
    def __init__(self, road_temperature: float, *, minutes_ago: float = 0.0):
        self.road_temperature = road_temperature
        self.timestamp = timezone.now() - timedelta(minutes=minutes_ago)


class IceWarningEvaluationTests(SimpleTestCase):
    def test_none_normal_conditions(self):
        self.assertEqual(evaluate_ice_warning(5.0, 2.0, 50.0), ICE_WARNING_NONE)
        self.assertEqual(evaluate_ice_warning(3.0, 1.0, 80.0), ICE_WARNING_NONE)

    def test_possible_slip(self):
        self.assertEqual(evaluate_ice_warning(2.0, 0.5, 80.0), ICE_WARNING_POSSIBLE_SLIP)
        self.assertEqual(evaluate_ice_warning(1.8, 0.0, 70.0), ICE_WARNING_POSSIBLE_SLIP)

    def test_increased_ice_by_temperature_and_dew_point(self):
        self.assertEqual(evaluate_ice_warning(1.0, 0.5, 80.0), ICE_WARNING_INCREASED_ICE)
        self.assertEqual(evaluate_ice_warning(0.5, 1.2, 70.0), ICE_WARNING_INCREASED_ICE)

    def test_increased_ice_by_humidity(self):
        self.assertEqual(evaluate_ice_warning(1.5, 5.0, 90.0), ICE_WARNING_INCREASED_ICE)
        self.assertEqual(evaluate_ice_warning(1.0, 4.0, 95.0), ICE_WARNING_INCREASED_ICE)

    def test_acute_ice(self):
        self.assertEqual(evaluate_ice_warning(0.0, 0.3, 80.0), ICE_WARNING_ACUTE_ICE)
        self.assertEqual(evaluate_ice_warning(-1.0, -0.8, 92.0), ICE_WARNING_ACUTE_ICE)

    def test_acute_ice_with_precipitation(self):
        self.assertEqual(
            evaluate_ice_warning(0.0, 3.0, 80.0, precipitation=True),
            ICE_WARNING_ACUTE_ICE,
        )

    def test_most_severe_level_wins(self):
        self.assertEqual(evaluate_ice_warning(0.0, 0.0, 95.0), ICE_WARNING_ACUTE_ICE)


class IceWarningHysteresisTests(SimpleTestCase):
    def _transition(
        self,
        stored_level,
        road,
        *,
        dew=0.0,
        humidity=80.0,
        recent=None,
        precipitation=False,
    ):
        return transition_ice_warning_level(
            stored_level=stored_level,
            road_temperature=road,
            air_temperature=road,
            humidity=humidity,
            dew_point=dew,
            precipitation=precipitation,
            recent_readings=recent or [],
        )

    def test_advisory_holds_until_reset_above_2_5(self):
        self.assertEqual(
            self._transition(ICE_WARNING_POSSIBLE_SLIP, 2.2, dew=0.0),
            ICE_WARNING_POSSIBLE_SLIP,
        )
        self.assertEqual(
            self._transition(ICE_WARNING_POSSIBLE_SLIP, 2.6, dew=0.0),
            ICE_WARNING_NONE,
        )

    def test_warning_holds_until_reset_above_1_5(self):
        self.assertEqual(
            self._transition(ICE_WARNING_INCREASED_ICE, 1.2, dew=0.0),
            ICE_WARNING_INCREASED_ICE,
        )
        self.assertEqual(
            self._transition(ICE_WARNING_INCREASED_ICE, 1.6, dew=0.0),
            ICE_WARNING_POSSIBLE_SLIP,
        )

    def test_escalation_is_immediate(self):
        self.assertEqual(
            self._transition(ICE_WARNING_POSSIBLE_SLIP, 0.0, dew=0.2),
            ICE_WARNING_ACUTE_ICE,
        )

    def test_critical_reset_requires_ten_minutes_above_0_5(self):
        recent_short = [
            _ReadingStub(0.7, minutes_ago=9),
            _ReadingStub(0.7, minutes_ago=0),
        ]
        self.assertEqual(
            self._transition(
                ICE_WARNING_ACUTE_ICE,
                0.7,
                dew=2.0,
                recent=recent_short,
            ),
            ICE_WARNING_ACUTE_ICE,
        )

        recent_long = [
            _ReadingStub(0.7, minutes_ago=11),
            _ReadingStub(0.7, minutes_ago=5),
            _ReadingStub(0.7, minutes_ago=0),
        ]
        self.assertEqual(
            self._transition(
                ICE_WARNING_ACUTE_ICE,
                0.7,
                dew=2.0,
                recent=recent_long,
            ),
            ICE_WARNING_POSSIBLE_SLIP,
        )

    def test_alert_status_mapping(self):
        self.assertEqual(alert_status_for_level(ICE_WARNING_NONE), 'green')
        self.assertEqual(alert_status_for_level(ICE_WARNING_POSSIBLE_SLIP), 'yellow')
        self.assertEqual(alert_status_for_level(ICE_WARNING_INCREASED_ICE), 'orange')
        self.assertEqual(alert_status_for_level(ICE_WARNING_ACUTE_ICE), 'red')
