from django.test import SimpleTestCase

from core.ice_warning import (
    ICE_WARNING_ACUTE_ICE,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
    alert_status_for_level,
    evaluate_ice_warning,
)


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

    def test_most_severe_level_wins(self):
        self.assertEqual(evaluate_ice_warning(0.0, 0.0, 95.0), ICE_WARNING_ACUTE_ICE)

    def test_alert_status_mapping(self):
        self.assertEqual(alert_status_for_level(ICE_WARNING_NONE), 'green')
        self.assertEqual(alert_status_for_level(ICE_WARNING_POSSIBLE_SLIP), 'yellow')
        self.assertEqual(alert_status_for_level(ICE_WARNING_INCREASED_ICE), 'orange')
        self.assertEqual(alert_status_for_level(ICE_WARNING_ACUTE_ICE), 'red')
