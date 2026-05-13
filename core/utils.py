import math


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
    if delta >= 0.5:
        return 'rising'
    if delta <= -0.5:
        return 'falling'
    return 'stable'
