import re
from decimal import Decimal

# Standortbezeichnung / ChirpStack deviceName, e.g. KOE-TPK-0005-N50.37151-E11.83813
DEVICE_NAME_COORDINATES = re.compile(
    r'-N(?P<lat>\d+(?:\.\d+)?)-E(?P<lon>\d+(?:\.\d+)?)',
    re.IGNORECASE,
)


def coordinates_from_device_name(device_name: str) -> tuple[Decimal, Decimal] | None:
    match = DEVICE_NAME_COORDINATES.search(device_name or '')
    if not match:
        return None
    return Decimal(match.group('lat')), Decimal(match.group('lon'))
