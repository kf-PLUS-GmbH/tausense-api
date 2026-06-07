from django.db.models import F, OuterRef, Subquery

from alerts.models import AlertRule
from alerts.services import evaluate_rule, status_from_trigger
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


def dashboard_warnings(municipality_id=None):
    qs = latest_readings_with_previous(municipality_id=municipality_id)
    data = {}
    rules = AlertRule.objects.filter(active=True, municipality__isnull=False, sensor__isnull=True)
    for reading in qs:
        municipality = reading.sensor.municipality
        if municipality is None:
            continue
        municipality_name = municipality.name
        if municipality_name not in data:
            data[municipality_name] = 0
        for rule in rules.filter(municipality=municipality):
            triggered, _ = evaluate_rule(rule, reading)
            if triggered:
                data[municipality_name] += 1
                break
    return [{'municipality': key, 'warning_count': value} for key, value in data.items()]


def dashboard_coldest_sensor(municipality_id=None):
    qs = latest_readings_with_previous(municipality_id=municipality_id).order_by('road_temperature')
    reading = qs.first()
    if not reading:
        return None
    return {
        'sensor_id': reading.sensor_id,
        'sensor_name': reading.sensor.name,
        'municipality': (
            reading.sensor.municipality.name if reading.sensor.municipality else None
        ),
        'road_temperature': reading.road_temperature,
        'air_temperature': reading.air_temperature,
        'dew_point': calculate_dew_point(reading.air_temperature, reading.humidity),
        'timestamp': reading.timestamp,
    }


def dashboard_map_data(municipality_id=None):
    sensor_qs = Sensor.objects.select_related('municipality').filter(active=True)
    if municipality_id:
        sensor_qs = sensor_qs.filter(municipality_id=municipality_id)

    latest_by_sensor = {
        r.sensor_id: r for r in latest_readings_with_previous(municipality_id=municipality_id)
    }
    rules = AlertRule.objects.filter(active=True).select_related('municipality', 'sensor')
    payload = []
    for sensor in sensor_qs:
        reading = latest_by_sensor.get(sensor.id)
        if reading is None:
            continue
        trend = calculate_trend(reading.air_temperature, reading.previous_air_temperature)
        applicable = rules.filter(sensor=sensor)
        if sensor.municipality_id:
            applicable = applicable | rules.filter(
                municipality=sensor.municipality,
                sensor__isnull=True,
            )
        triggered = any(evaluate_rule(rule, reading)[0] for rule in applicable)
        payload.append(
            {
                'sensor_id': sensor.id,
                'sensor_name': sensor.name,
                'municipality': sensor.municipality.name if sensor.municipality else None,
                'coordinates': {'lat': float(sensor.latitude), 'lon': float(sensor.longitude)},
                'latest_reading': {
                    'timestamp': reading.timestamp,
                    'air_temperature': reading.air_temperature,
                    'road_temperature': reading.road_temperature,
                    'humidity': reading.humidity,
                    'dew_point': calculate_dew_point(reading.air_temperature, reading.humidity),
                    'trend': trend,
                },
                'alert_status': status_from_trigger(triggered),
            }
        )
    return payload
