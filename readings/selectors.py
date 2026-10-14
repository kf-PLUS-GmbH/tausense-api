from django.db import connection
from django.db.models import F, OuterRef, Q, Subquery

from readings.models import SensorReading


def filtered_readings(sensor_id=None, municipality_id=None, time_from=None, time_to=None):
    queryset = SensorReading.objects.select_related('sensor', 'sensor__municipality')
    if sensor_id:
        queryset = queryset.filter(sensor_id=sensor_id)
    if municipality_id:
        queryset = queryset.filter(sensor__municipality_id=municipality_id)
    if time_from:
        queryset = queryset.filter(timestamp__gte=time_from)
    if time_to:
        queryset = queryset.filter(timestamp__lte=time_to)
    return queryset


def _scope_readings(*, sensor_id=None, municipality_id=None):
    scoped = SensorReading.objects.all()
    if sensor_id:
        scoped = scoped.filter(sensor_id=sensor_id)
    if municipality_id:
        scoped = scoped.filter(sensor__municipality_id=municipality_id)
    return scoped


def latest_readings_queryset(sensor_id=None, municipality_id=None):
    """Latest reading per sensor (no previous-air-temp annotation)."""
    if connection.vendor == 'postgresql':
        latest_ids = (
            _scope_readings(sensor_id=sensor_id, municipality_id=municipality_id)
            .order_by('sensor_id', '-timestamp', '-id')
            .distinct('sensor_id')
            .values('pk')
        )
        return (
            SensorReading.objects.filter(pk__in=Subquery(latest_ids))
            .select_related('sensor', 'sensor__municipality')
        )

    filters = Q()
    if sensor_id:
        filters &= Q(sensor_id=sensor_id)
    if municipality_id:
        filters &= Q(sensor__municipality_id=municipality_id)

    latest_ts = (
        SensorReading.objects.filter(sensor_id=OuterRef('sensor_id'))
        .order_by('-timestamp', '-id')
        .values('timestamp')[:1]
    )
    return (
        SensorReading.objects.select_related('sensor', 'sensor__municipality')
        .filter(filters)
        .annotate(_latest_timestamp=Subquery(latest_ts))
        .filter(timestamp=F('_latest_timestamp'))
    )


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
    latest_ids = (
        _scope_readings(municipality_id=municipality_id)
        .order_by('sensor_id', '-timestamp', '-id')
        .distinct('sensor_id')
        .values('pk')
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
        SensorReading.objects.filter(pk__in=Subquery(latest_ids))
        .select_related('sensor', 'sensor__municipality')
        .annotate(previous_air_temperature=Subquery(previous_temp))
    )


def _latest_readings_correlated(municipality_id=None):
    base = _scope_readings(municipality_id=municipality_id)

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
