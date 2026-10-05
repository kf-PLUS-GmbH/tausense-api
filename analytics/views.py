import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.serializers import UsageAnalyticsUploadSerializer
from analytics.services import ingest_usage_analytics

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class UsageAnalyticsUploadView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Analytics'],
        request=UsageAnalyticsUploadSerializer,
        responses={202: dict},
        examples=[
            OpenApiExample(
                'Daily usage snapshot',
                value={
                    'schema_version': 1,
                    'installation_id': '550e8400-e29b-41d4-a716-446655440000',
                    'updated_at': '2026-04-11T09:41:00.000Z',
                    'days': {
                        '2026-04-11': {
                            'sessions': 2,
                            'last_active_at': '2026-04-11T09:30:00.000Z',
                            'screens': {'map': 5, 'dashboard': 2},
                            'actions': {'location_button': 1},
                            'camera_enabled': True,
                            'filters': {
                                'status:orange': 2,
                                'municipalities': {'Hof': 2},
                                'sensor_ids': {'14': 2},
                            },
                            'connectivity_sessions': {'wifi': 2, 'mobile': 0},
                            'connectivity': {'wifi': 1, 'mobile': 1},
                        },
                    },
                },
                request_only=True,
            )
        ],
        description=(
            'Consent-based usage analytics upload from the Flutter app. '
            'Aggregates are merged per installation_id; no personal data is required.'
        ),
    )
    def post(self, request):
        serializer = UsageAnalyticsUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning('Invalid usage analytics payload: %s', serializer.errors)
            serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        record = ingest_usage_analytics(
            installation_id=data['installation_id'],
            schema_version=data['schema_version'],
            updated_at=data.get('updated_at'),
            days=data.get('days') or {},
        )
        return Response(
            {
                'status': 'accepted',
                'installation_id': str(record.installation_id),
                'day_count': record.day_count,
            },
            status=status.HTTP_202_ACCEPTED,
        )
