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


def latest_readings_queryset(sensor_id=None, municipality_id=None):
    filters = Q()
    if sensor_id:
        filters &= Q(sensor_id=sensor_id)
    if municipality_id:
        filters &= Q(sensor__municipality_id=municipality_id)

    latest_ts = (
        SensorReading.objects.filter(sensor_id=OuterRef('sensor_id'))
        .order_by('-timestamp')
        .values('timestamp')[:1]
    )
    return (
        SensorReading.objects.select_related('sensor', 'sensor__municipality')
        .filter(filters)
        .annotate(_latest_timestamp=Subquery(latest_ts))
        .filter(timestamp=F('_latest_timestamp'))
    )
