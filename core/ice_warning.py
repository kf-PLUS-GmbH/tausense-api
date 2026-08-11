ICE_WARNING_NONE = 'none'
ICE_WARNING_POSSIBLE_SLIP = 'possible_slip'
ICE_WARNING_INCREASED_ICE = 'increased_ice'
ICE_WARNING_ACUTE_ICE = 'acute_ice'

ICE_WARNING_LEVELS = (
    ICE_WARNING_NONE,
    ICE_WARNING_POSSIBLE_SLIP,
    ICE_WARNING_INCREASED_ICE,
    ICE_WARNING_ACUTE_ICE,
)

ICE_WARNING_LABELS = {
    ICE_WARNING_NONE: 'Keine Warnung',
    ICE_WARNING_POSSIBLE_SLIP: 'Mögliche Rutschgefahr',
    ICE_WARNING_INCREASED_ICE: 'Erhöhte Eisgefahr',
    ICE_WARNING_ACUTE_ICE: 'Akute Eisbildung wahrscheinlich',
}

ALERT_STATUS_BY_LEVEL = {
    ICE_WARNING_NONE: 'green',
    ICE_WARNING_POSSIBLE_SLIP: 'yellow',
    ICE_WARNING_INCREASED_ICE: 'orange',
    ICE_WARNING_ACUTE_ICE: 'red',
}

ICE_WARNING_SEVERITY = {
    ICE_WARNING_NONE: 0,
    ICE_WARNING_POSSIBLE_SLIP: 1,
    ICE_WARNING_INCREASED_ICE: 2,
    ICE_WARNING_ACUTE_ICE: 3,
}


def evaluate_ice_warning(road_temperature: float, dew_point: float, humidity: float) -> str:
    """
    Classify ice/slip risk from road temperature, dew point and relative humidity.

    Checks most severe level first:
    - acute: road <= 0 °C and |road - dew| <= 0.5 °C
    - increased: (road <= 1 °C and |road - dew| <= 1 °C) or (humidity >= 90 % and road <= 1.5 °C)
    - possible slip: road <= 2 °C and |road - dew| <= 2 °C
    """
    diff = abs(road_temperature - dew_point)

    if road_temperature <= 0.0 and diff <= 0.5:
        return ICE_WARNING_ACUTE_ICE

    if (road_temperature <= 1.0 and diff <= 1.0) or (
        humidity >= 90.0 and road_temperature <= 1.5
    ):
        return ICE_WARNING_INCREASED_ICE

    if road_temperature <= 2.0 and diff <= 2.0:
        return ICE_WARNING_POSSIBLE_SLIP

    return ICE_WARNING_NONE


def alert_status_for_level(level: str) -> str:
    return ALERT_STATUS_BY_LEVEL.get(level, 'gray')
