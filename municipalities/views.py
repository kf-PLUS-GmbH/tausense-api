from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import mixins, viewsets

from municipalities.models import Municipality
from municipalities.serializers import MunicipalitySerializer


@extend_schema(
    tags=['Municipalities'],
    responses={
        200: OpenApiResponse(
            response=MunicipalitySerializer,
            description='Municipality list/detail with GeoJSON boundary.',
            examples=[
                OpenApiExample(
                    'Municipality Example',
                    value={
                        'id': 1,
                        'name': 'Hof',
                        'geo_boundary': {
                            'type': 'Polygon',
                            'coordinates': [[[11.9, 50.3], [11.95, 50.3], [11.95, 50.35], [11.9, 50.3]]],
                        },
                    },
                )
            ],
        )
    },
)
class MunicipalityViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Municipality.objects.all().order_by('name')
    serializer_class = MunicipalitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        name = (self.request.query_params.get('name') or '').strip()
        if name:
            queryset = queryset.filter(name__iexact=name)
        return queryset
