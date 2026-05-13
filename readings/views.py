from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from readings.selectors import filtered_readings, latest_readings_queryset
from readings.serializers import SensorReadingSerializer


@extend_schema(
    tags=['Readings'],
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
                        'municipality': 1,
                        'timestamp': '2026-05-12T08:30:00Z',
                        'air_temperature': 1.8,
                        'road_temperature': -0.4,
                        'humidity': 86.0,
                        'dew_point': -0.25,
                        'trend': 'falling',
                        'raw_data': {'battery': 91},
                    },
                )
            ],
        )
    },
)
class SensorReadingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SensorReadingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sensor', 'sensor__municipality']

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
