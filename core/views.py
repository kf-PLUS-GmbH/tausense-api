from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response

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
        description='Count of sensors above configured thresholds grouped by municipality.',
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
                            'municipality': 'Hof',
                            'road_temperature': -4.2,
                            'air_temperature': -1.1,
                            'dew_point': -2.35,
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
        description='Map-ready sensors with coordinates, latest reading, trend and alert status.',
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
                                'municipality': 'Hof',
                                'coordinates': {'lat': 50.321, 'lon': 11.924},
                                'latest_reading': {
                                    'timestamp': '2026-05-12T08:30:00Z',
                                    'air_temperature': 1.8,
                                    'road_temperature': -0.4,
                                    'humidity': 86.0,
                                    'dew_point': -0.25,
                                    'trend': 'falling',
                                },
                                'alert_status': 'red',
                            }
                        ],
                    )
                ],
            )
        },
    )
    def get(self, request):
        return Response(dashboard_map_data(request.query_params.get('municipality')))
