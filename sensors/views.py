from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets

from sensors.models import Sensor
from sensors.serializers import SensorSerializer


@extend_schema(
    tags=['Sensors'],
    responses={
        200: OpenApiResponse(
            response=SensorSerializer,
            description='Sensor list/detail endpoint.',
            examples=[
                OpenApiExample(
                    'Sensor Example',
                    value={
                        'id': 5,
                        'name': 'B173 Hof Nord',
                        'municipality': 1,
                        'municipality_name': 'Hof',
                        'latitude': 50.321,
                        'longitude': 11.924,
                        'sensor_type': 'standard',
                        'active': True,
                        'external_id': 'HOF-005',
                    },
                )
            ],
        )
    },
)
class SensorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Sensor.objects.select_related('municipality').all()
    serializer_class = SensorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['municipality', 'active', 'sensor_type']
