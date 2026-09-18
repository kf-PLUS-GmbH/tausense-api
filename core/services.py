from django.db.models import F, OuterRef, Subquery

from core.ice_warning import (
    ICE_WARNING_LABELS,
    ICE_WARNING_NONE,
    alert_status_for_level,
    evaluate_ice_warning,
)
from core.utils import calculate_dew_point, calculate_trend
from readings.models import SensorReading
from sensors.models import Sensor


def latest_readings_with_previous(municipality_id=None):
    base = SensorReading.objects.all()
    if municipality_id:
        base = base.filter(sensor__municipality_id=municipality_id)

    latest_timestamp = (
        SensorReading.objects.filter(sensor_id=OuterRef('sensor_id'))
        .order_by('-timestamp')
        .values('timestamp')[:1]
    )
    previous_temp = (
        SensorReading.objects.filter(
            sensor_id=OuterRef('sensor_id'),
            timestamp__lt=OuterRef('timestamp'),
        )
        .order_by('-timestamp')
        .values('air_temperature')[:1]
    )
    return (
        base.select_related('sensor', 'sensor__municipality')
        .annotate(_latest_ts=Subquery(latest_timestamp))
        .filter(timestamp=F('_latest_ts'))
        .annotate(previous_air_temperature=Subquery(previous_temp))
    )


def _ice_warning_for_reading(reading):
    dew_point = calculate_dew_point(reading.air_temperature, reading.humidity)
    level = evaluate_ice_warning(reading.road_temperature, dew_point, reading.humidity)
    return level, dew_point


def dashboard_warnings(municipality_id=None):
    qs = latest_readings_with_previous(municipality_id=municipality_id)
    data = {}
    for reading in qs:
        municipality = reading.sensor.municipality
        if municipality is None:
            continue
        level, _ = _ice_warning_for_reading(reading)
        if level == ICE_WARNING_NONE:
            continue
        municipality_name = municipality.name
        data[municipality_name] = data.get(municipality_name, 0) + 1
    return [{'municipality': key, 'warning_count': value} for key, value in data.items()]


def dashboard_coldest_sensor(municipality_id=None):
    qs = latest_readings_with_previous(municipality_id=municipality_id).order_by('road_temperature')
    reading = qs.first()
    if not reading:
        return None
    sensor_name = reading.sensor.display_name or reading.sensor.name
    return {
        'sensor_id': reading.sensor_id,
        'sensor_name': sensor_name,
        'device_name': reading.device_name,
        'municipality': (
            reading.sensor.municipality.name if reading.sensor.municipality else None
        ),
        'road_temperature': reading.road_temperature,
        'air_temperature': reading.air_temperature,
        'dew_point': calculate_dew_point(reading.air_temperature, reading.humidity),
        'battery_voltage': reading.battery_voltage,
        'timestamp': reading.timestamp,
    }


def dashboard_map_data(municipality_id=None, since=None):
    sensor_qs = Sensor.objects.select_related('municipality').filter(active=True)
    if municipality_id:
        sensor_qs = sensor_qs.filter(municipality_id=municipality_id)

    latest_by_sensor = {
        r.sensor_id: r for r in latest_readings_with_previous(municipality_id=municipality_id)
    }
    payload = []
    for sensor in sensor_qs:
        reading = latest_by_sensor.get(sensor.id)
        if reading is None:
            continue
        if since and reading.timestamp <= since and sensor.updated_at <= since:
            continue
        trend = calculate_trend(reading.air_temperature, reading.previous_air_temperature)
        ice_warning_level, dew_point = _ice_warning_for_reading(reading)
        # Install position from sensor metadata (XLSX / deviceName); not gateway GPS on readings.
        latitude = sensor.latitude if sensor.latitude is not None else reading.latitude
        longitude = sensor.longitude if sensor.longitude is not None else reading.longitude
        if latitude is None or longitude is None:
            continue
        sensor_name = sensor.display_name or sensor.name
        payload.append(
            {
                'sensor_id': sensor.id,
                'sensor_name': sensor_name,
                'device_name': sensor.device_name,
                'operator_name': sensor.operator_name,
                'municipality': sensor.municipality.name if sensor.municipality else None,
                'coordinates': {'lat': float(latitude), 'lon': float(longitude)},
                'updated_at': sensor.updated_at,
                'latest_reading': {
                    'timestamp': reading.timestamp,
                    'device_name': reading.device_name,
                    'air_temperature': reading.air_temperature,
                    'road_temperature': reading.road_temperature,
                    'humidity': reading.humidity,
                    'air_temperature_radiation_shield': reading.air_temperature_radiation_shield,
                    'air_humidity_radiation_shield': reading.air_humidity_radiation_shield,
                    'air_temperature_unshielded': reading.air_temperature_unshielded,
                    'air_humidity_unshielded': reading.air_humidity_unshielded,
                    'dew_point': dew_point,
                    'reported_dew_point': reading.reported_dew_point,
                    'trend': trend,
                    'angle': reading.angle,
                    'sensor_temperature': reading.sensor_temperature,
                    'battery_voltage': reading.battery_voltage,
                },
                'ice_warning_level': ice_warning_level,
                'ice_warning_label': ICE_WARNING_LABELS[ice_warning_level],
                'alert_status': alert_status_for_level(ice_warning_level),
            }
        )
    return payload
