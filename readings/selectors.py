from django.db import connection
from django.db.models import F, OuterRef, Subquery

from readings.models import SensorReading


def latest_readings_with_previous(municipality_id=None):
    """
    Latest SensorReading per sensor plus previous air temperature (for trend).

    PostgreSQL: DISTINCT ON (latest row per sensor) + previous air temp only on those rows.
    Fallback: legacy correlated subqueries over all readings (slow on large tables).
    """
    if connection.vendor == 'postgresql':
        return _latest_readings_distinct_on(municipality_id)
    return _latest_readings_correlated(municipality_id)


def _latest_readings_distinct_on(municipality_id=None):
    scoped = SensorReading.objects.all()
    if municipality_id:
        scoped = scoped.filter(sensor__municipality_id=municipality_id)

    latest_ids = scoped.order_by('sensor_id', '-timestamp', '-id').distinct('sensor_id').values('pk')

    previous_temp = (
        SensorReading.objects.filter(
            sensor_id=OuterRef('sensor_id'),
            timestamp__lt=OuterRef('timestamp'),
        )
        .order_by('-timestamp', '-id')
        .values('air_temperature')[:1]
    )

    return (
        SensorReading.objects.filter(pk__in=Subquery(latest_ids))
        .select_related('sensor', 'sensor__municipality')
        .annotate(previous_air_temperature=Subquery(previous_temp))
    )


def _latest_readings_correlated(municipality_id=None):
    base = SensorReading.objects.all()
    if municipality_id:
        base = base.filter(sensor__municipality_id=municipality_id)

    latest_timestamp = (
        SensorReading.objects.filter(sensor_id=OuterRef('sensor_id'))
        .order_by('-timestamp', '-id')
        .values('timestamp')[:1]
    )
    previous_temp = (
        SensorReading.objects.filter(
            sensor_id=OuterRef('sensor_id'),
            timestamp__lt=OuterRef('timestamp'),
        )
        .order_by('-timestamp', '-id')
        .values('air_temperature')[:1]
    )
    return (
        base.select_related('sensor', 'sensor__municipality')
        .annotate(_latest_ts=Subquery(latest_timestamp))
        .filter(timestamp=F('_latest_ts'))
        .annotate(previous_air_temperature=Subquery(previous_temp))
    )
