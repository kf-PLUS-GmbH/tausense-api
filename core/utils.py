import math

TREND_DELTA_THRESHOLD = 0.2


def calculate_dew_point(air_temperature: float, humidity: float) -> float:
    """
    Magnus formula approximation for dew point in Celsius.
    """
    humidity = max(0.1, min(humidity, 100.0))
    a = 17.62
    b = 243.12
    gamma = (a * air_temperature) / (b + air_temperature) + math.log(humidity / 100.0)
    return round((b * gamma) / (a - gamma), 2)


def calculate_trend(current_value: float, previous_value: float | None) -> str:
    if previous_value is None:
        return 'stable'
    delta = current_value - previous_value
    if delta >= TREND_DELTA_THRESHOLD:
        return 'rising'
    if delta <= -TREND_DELTA_THRESHOLD:
        return 'falling'
    return 'stable'
