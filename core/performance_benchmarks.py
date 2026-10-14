from __future__ import annotations

from core.query_profiling import profile_callable, profile_steps
from core.services import (
    dashboard_coldest_sensor,
    dashboard_map_data,
    dashboard_map_data_legacy_warnings,
    dashboard_warnings,
    latest_readings_with_previous,
)
from sensors.models import Sensor


def run_benchmark(benchmark_id: str):
    if benchmark_id == 'map_data':
        return profile_callable(
            'GET /api/v1/dashboard/map-data/',
            dashboard_map_data,
        )
    if benchmark_id == 'map_data_legacy_warnings':
        return profile_callable(
            'Map-Daten (Warnstufe pro Sensor neu berechnet)',
            dashboard_map_data_legacy_warnings,
        )
    if benchmark_id == 'warnings':
        return profile_callable(
            'GET /api/v1/dashboard/warnings/',
            dashboard_warnings,
        )
    if benchmark_id == 'coldest':
        return profile_callable(
            'GET /api/v1/dashboard/coldest-sensor/',
            dashboard_coldest_sensor,
        )
    if benchmark_id == 'map_data_breakdown':
        return profile_map_data_breakdown()
    raise ValueError(f'Unknown benchmark: {benchmark_id}')


def profile_map_data_breakdown():
    sensor_count = Sensor.objects.filter(active=True).count()
    readings_count_holder: dict[str, int] = {'value': 0}

    def load_latest_readings():
        readings = list(
            latest_readings_with_previous().order_by('sensor_id', '-timestamp', '-id'),
        )
        readings_count_holder['value'] = len(readings)
        return readings_count_holder['value']

    steps = [
        ('Aktive Sensoren zählen', lambda: sensor_count),
        ('Neueste Messungen laden (Subquery)', load_latest_readings),
        ('Map-Payload bauen (gesamt)', dashboard_map_data),
    ]
    profile = profile_steps('Map-Daten – Schrittweise', steps)
    profile.result_summary['active_sensors'] = sensor_count
    profile.result_summary['latest_readings'] = readings_count_holder['value']
    return profile


BENCHMARK_CHOICES = (
    ('map_data', 'Map-Daten (Produktion)'),
    ('map_data_breakdown', 'Map-Daten – Schritte'),
    ('map_data_legacy_warnings', 'Map-Daten – alte Warnlogik (Vergleich)'),
    ('warnings', 'Dashboard-Warnungen'),
    ('coldest', 'Kältester Sensor'),
)
