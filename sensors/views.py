from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from sensors.models import Sensor
from sensors.serializers import SensorOperatorSerializer, SensorSerializer


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
                        'name': 'Münchberg 1',
                        'device_name': 'MUB-TPK-0001-N50.22764-E11.76708',
                        'operator_name': 'Münchberg',
                        'display_name': 'Münchberg 1',
                        'location_description': 'Meierhof - Jehsen, Wasserhochbehälter',
                        'what3words': '///nachgeholt.drin.linien',
                        'municipality': 1,
                        'municipality_name': 'Münchberg',
                        'latitude': 50.22764,
                        'longitude': 11.76708,
                        'sensor_type': 'standard',
                        'active': True,
                        'external_id': '70B3D57BA000638D',
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
    filterset_fields = ['municipality', 'active', 'sensor_type', 'device_name', 'operator_name']

    @extend_schema(
        tags=['Sensors'],
        description='Distinct operator/place names for Flutter filter dropdowns.',
        responses=SensorOperatorSerializer(many=True),
        examples=[
            OpenApiExample(
                'Operator Choices Example',
                value=[
                    {'operator_name': 'Naila', 'sensor_count': 5},
                    {'operator_name': 'Münchberg', 'sensor_count': 5},
                ],
            )
        ],
    )
    @action(detail=False, methods=['get'], url_path='operators')
    def operators(self, request):
        queryset = (
            Sensor.objects.exclude(operator_name='')
            .values('operator_name')
            .annotate(sensor_count=Count('id'))
            .order_by('operator_name')
        )
        return Response(list(queryset))
