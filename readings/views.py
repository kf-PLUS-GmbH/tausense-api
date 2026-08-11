from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from readings.selectors import filtered_readings, latest_readings_queryset
from readings.serializers import ReadingHistoryResponseSerializer, SensorReadingSerializer
from readings.services.history import HistoryRangeError, MAX_HISTORY_DAYS, build_reading_history


@extend_schema(
    tags=['Readings'],
    parameters=[
        OpenApiParameter('sensor', int, description='Optional sensor id filter.'),
        OpenApiParameter('municipality', int, description='Optional municipality id filter.'),
        OpenApiParameter('from', str, description='Optional ISO timestamp lower bound.'),
        OpenApiParameter('to', str, description='Optional ISO timestamp upper bound.'),
    ],
    responses={
        200: OpenApiResponse(
            response=SensorReadingSerializer,
            description='Reading list endpoint with filters and computed fields.',
            examples=[
                OpenApiExample(
                    'Reading Example',
                    value={
                        'id': 42,
                        'sensor': 5,
                        'device_name': 'MUB-TPK-0001-N50.22764-E11.76708',
                        'municipality': 1,
                        'timestamp': '2026-05-12T08:30:00Z',
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
                        'latitude': 50.22764,
                        'longitude': 11.76708,
                    },
                )
            ],
        )
    },
)
class SensorReadingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SensorReadingSerializer

    def get_queryset(self):
        return filtered_readings(
            sensor_id=self.request.query_params.get('sensor'),
            municipality_id=self.request.query_params.get('municipality'),
            time_from=self.request.query_params.get('from'),
            time_to=self.request.query_params.get('to'),
        )

    @extend_schema(
        description='Returns latest reading for each sensor within optional filter scope.',
        responses=SensorReadingSerializer(many=True),
    )
    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        sensor = request.query_params.get('sensor')
        municipality = request.query_params.get('municipality')
        queryset = latest_readings_queryset(sensor_id=sensor, municipality_id=municipality)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        description=(
            'Chart-ready reading history for one sensor. '
            f'Returns up to {MAX_HISTORY_DAYS} days of measurements ordered by timestamp.'
        ),
        parameters=[
            OpenApiParameter(
                name='sensor',
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Sensor id.',
            ),
            OpenApiParameter(
                name='days',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f'Lookback in days (1-{MAX_HISTORY_DAYS}, default 7). Ignored when from/to are set.',
            ),
            OpenApiParameter(
                name='from',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Optional ISO timestamp lower bound (requires to).',
            ),
            OpenApiParameter(
                name='to',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Optional ISO timestamp upper bound (requires from).',
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=ReadingHistoryResponseSerializer,
                examples=[
                    OpenApiExample(
                        'Reading history',
                        value={
                            'sensor_id': 60,
                            'sensor_name': 'Stammbach 1',
                            'from': '2026-07-23T10:51:00Z',
                            'to': '2026-07-30T10:51:00Z',
                            'days': 7,
                            'count': 2,
                            'points': [
                                {
                                    'timestamp': '2026-07-29T08:00:00Z',
                                    'air_temperature': 2.1,
                                    'road_temperature': 1.4,
                                    'humidity': 84.0,
                                    'air_temperature_radiation_shield': 2.1,
                                    'air_humidity_radiation_shield': 84.0,
                                    'air_temperature_unshielded': 2.4,
                                    'air_humidity_unshielded': 81.0,
                                    'dew_point': 0.2,
                                    'reported_dew_point': 0.1,
                                    'angle': 48.0,
                                    'sensor_temperature': 2.0,
                                    'battery_voltage': 2.8,
                                    'ice_warning_level': 'possible_slip',
                                    'alert_status': 'yellow',
                                }
                            ],
                        },
                    )
                ],
            )
        },
    )
    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        sensor_id = request.query_params.get('sensor')
        if not sensor_id:
            return Response({'detail': 'sensor is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sensor_id = int(sensor_id)
        except (TypeError, ValueError):
            return Response({'detail': 'sensor must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        days_param = request.query_params.get('days')
        days = None
        if days_param not in (None, ''):
            try:
                days = int(days_param)
            except ValueError:
                return Response({'detail': 'days must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = build_reading_history(
                sensor_id=sensor_id,
                days=days,
                time_from=request.query_params.get('from'),
                time_to=request.query_params.get('to'),
            )
        except HistoryRangeError as exc:
            body = {'detail': exc.message}
            if exc.field:
                body['field'] = exc.field
            return Response(body, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReadingHistoryResponseSerializer(payload)
        return Response(serializer.data)
