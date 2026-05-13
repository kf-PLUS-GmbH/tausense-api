from alerts.models import AlertRule
from core.utils import calculate_dew_point


def evaluate_rule(rule, reading):
    if rule.threshold_type == AlertRule.THRESHOLD_DEW_POINT:
        value = calculate_dew_point(reading.air_temperature, reading.humidity)
    else:
        value = reading.air_temperature

    operations = {
        AlertRule.OP_GT: value > rule.threshold_value,
        AlertRule.OP_GTE: value >= rule.threshold_value,
        AlertRule.OP_LT: value < rule.threshold_value,
        AlertRule.OP_LTE: value <= rule.threshold_value,
    }
    return operations.get(rule.operator, False), value


def status_from_trigger(is_triggered):
    return 'red' if is_triggered else 'green'
