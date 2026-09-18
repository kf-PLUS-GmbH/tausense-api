from sensors.models import Sensor


def find_sensor_by_webhook_device_name(device_name: str) -> Sensor | None:
    """
    Match imported sensors (often long Standortbezeichnung with -N…-E… suffix)
    to webhook deviceName when the network server sends a shorter name.
    """
    name = (device_name or '').strip()
    if not name:
        return None

    exact = Sensor.objects.filter(device_name=name).first()
    if exact:
        return exact

    prefix_matches = Sensor.objects.filter(device_name__startswith=f'{name}-')
    if prefix_matches.count() == 1:
        return prefix_matches.first()

    return None
