from datetime import timezone as datetime_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services import dashboard_coldest_sensor, dashboard_map_data, dashboard_warnings
from core.serializers import (
    DashboardColdestSensorSerializer,
    DashboardMapSensorSerializer,
    DashboardWarningSerializer,
)


class DashboardWarningsView(APIView):
    @extend_schema(
        tags=['Dashboard'],
        parameters=[
            OpenApiParameter(
                name='municipality',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Optional municipality id filter.',
            )
        ],
        description='Count of sensors with ice warnings grouped by municipality.',
        responses={
            200: OpenApiResponse(
                response=DashboardWarningSerializer(many=True),
                description='Warning counts grouped by municipality.',
                examples=[
                    OpenApiExample(
                        'Warnings Example',
                        value=[
                            {'municipality': 'Hof', 'warning_count': 3},
                            {'municipality': 'Rehau', 'warning_count': 1},
                        ],
                    )
                ],
            )
        },
    )
    def get(self, request):
        return Response(dashboard_warnings(request.query_params.get('municipality')))


class DashboardColdestSensorView(APIView):
    @extend_schema(
        tags=['Dashboard'],
        parameters=[
            OpenApiParameter(
                name='municipality',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Optional municipality id filter.',
            )
        ],
        description='Returns coldest sensor by latest road temperature.',
        responses={
            200: OpenApiResponse(
                response=DashboardColdestSensorSerializer,
                description='Coldest sensor in current scope (or null if no readings exist).',
                examples=[
                    OpenApiExample(
                        'Coldest Sensor Example',
                        value={
                            'sensor_id': 5,
                            'sensor_name': 'B173 Hof Nord',
                            'device_name': 'MUB-TPK-0001-N50.22764-E11.76708',
                            'municipality': 'Hof',
                            'road_temperature': -4.2,
                            'air_temperature': -1.1,
                            'dew_point': -2.35,
                            'battery_voltage': 2.7,
                            'timestamp': '2026-05-12T08:30:00Z',
                        },
                    )
                ],
            )
        },
    )
    def get(self, request):
        data = dashboard_coldest_sensor(request.query_params.get('municipality'))
        return Response(data)


class DashboardMapDataView(APIView):
    def _parse_since(self, value):
        if not value:
            return None, None
        parsed = parse_datetime(value)
        if parsed is None:
            return None, Response(
                {'detail': 'Invalid since timestamp. Use ISO 8601 format.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, datetime_timezone.utc)
        return parsed, None

    @extend_schema(
        tags=['Dashboard'],
        parameters=[
            OpenApiParameter(
                name='municipality',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Optional municipality id filter.',
            ),
            OpenApiParameter(
                name='since',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    'Optional ISO timestamp for incremental sync. '
                    'Only sensors with changed metadata or newer readings are returned.'
                ),
            ),
        ],
        description=(
            'Map-ready sensors with coordinates, latest reading, trend and ice warning status. '
            'Warning levels are derived from road temperature, dew point and humidity.'
        ),
        responses={
            200: OpenApiResponse(
                response=DashboardMapSensorSerializer(many=True),
                description='Map-ready sensors and latest readings.',
                examples=[
                    OpenApiExample(
                        'Map Data Example',
                        value=[
                            {
                                'sensor_id': 5,
                                'sensor_name': 'B173 Hof Nord',
                                'device_name': 'MUB-TPK-0001-N50.22764-E11.76708',
                                'operator_name': 'Münchberg',
                                'municipality': 'Hof',
                                'coordinates': {'lat': 50.321, 'lon': 11.924},
                                'updated_at': '2026-05-12T08:30:00Z',
                                'latest_reading': {
                                    'timestamp': '2026-05-12T08:30:00Z',
                                    'device_name': 'MUB-TPK-0001-N50.22764-E11.76708',
                                    'air_temperature': 1.8,
                                    'road_temperature': -0.4,
                                    'humidity': 86.0,
                                    'air_temperature_radiation_shield': 1.8,
                                    'air_humidity_radiation_shield': 86.0,
                                    'air_temperature_unshielded': 2.2,
                                    'air_humidity_unshielded': 82.0,
                                    'dew_point': -0.25,
                                    'reported_dew_point': -0.3,
                                    'trend': 'falling',
                                    'angle': 51.0,
                                    'sensor_temperature': 1.5,
                                    'battery_voltage': 2.7,
                                },
                                'ice_warning_level': 'acute_ice',
                                'ice_warning_label': 'Akute Eisbildung wahrscheinlich',
                                'alert_status': 'red',
                            }
                        ],
                    )
                ],
            )
        },
    )
    def get(self, request):
        since, error_response = self._parse_since(request.query_params.get('since'))
        if error_response:
            return error_response

        response = Response(
            dashboard_map_data(
                municipality_id=request.query_params.get('municipality'),
                since=since,
            )
        )
        response['X-Sync-Timestamp'] = timezone.now().isoformat()
        return response
