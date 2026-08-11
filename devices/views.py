import logging
import os

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from devices.models import AlertPreference
from devices.serializers import (
    AlertPreferenceResponseSerializer,
    AlertPreferenceSerializer,
    PushTokenResponseSerializer,
    PushTokenSerializer,
    TestPushSerializer,
)
from devices.services.push import send_push_notification

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class AlertPreferencesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Alerts'],
        request=AlertPreferenceSerializer,
        responses={200: AlertPreferenceResponseSerializer},
        examples=[
            OpenApiExample(
                'Alert preferences',
                value={
                    'user_id': 'flutter-install-id',
                    'severity_filter': 'orange',
                    'notifications_enabled': True,
                    'selected_municipality': 'Hof',
                    'selected_sensor_ids': [1, 5, 12],
                },
                request_only=True,
            )
        ],
        description=(
            'Store or update push notification preferences for a local app user. '
            'severity_filter orange triggers orange and red alerts; red triggers red only.'
        ),
    )
    def post(self, request):
        serializer = AlertPreferenceSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            logger.warning('Invalid alert preferences payload: %s', serializer.errors)
            serializer.is_valid(raise_exception=True)
        preference = serializer.save()
        return Response(
            AlertPreferenceResponseSerializer(preference).data,
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class PushTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Devices'],
        request=PushTokenSerializer,
        responses={200: PushTokenResponseSerializer},
        examples=[
            OpenApiExample(
                'Register FCM token',
                value={
                    'user_id': 'flutter-install-id',
                    'fcm_token': 'fcm-device-token-here',
                    'platform': 'android',
                },
                request_only=True,
            )
        ],
        description='Register or update an FCM device token for remote push notifications.',
    )
    def post(self, request):
        serializer = PushTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        token = serializer.save()
        return Response(
            PushTokenResponseSerializer(token).data,
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TestPushView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Devices'],
        request=TestPushSerializer,
        examples=[
            OpenApiExample(
                'Test push',
                value={
                    'device_token': 'fcm-device-token-here',
                    'sensor_id': 5,
                    'alert_status': 'red',
                    'sensor_name': 'B173 Hof Nord',
                    'municipality_name': 'Hof',
                    'title': 'Test Warnung',
                    'body': 'Akute Eisbildung wahrscheinlich',
                },
                request_only=True,
            )
        ],
        description='Send a test push notification to one device token.',
    )
    def post(self, request):
        if not _test_push_enabled(request):
            return Response(
                {'detail': 'Test push endpoint is disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TestPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = send_push_notification(
            fcm_token=data['device_token'],
            sensor_id=data['sensor_id'],
            alert_status=data['alert_status'],
            sensor_name=data['sensor_name'],
            municipality_name=data.get('municipality_name') or '',
            title=data['title'],
            body=data['body'],
        )

        status_code = status.HTTP_200_OK if result.success else status.HTTP_502_BAD_GATEWAY
        return Response(
            {
                'success': result.success,
                'message_id': result.message_id,
                'error': result.error,
                'token_removed': result.token_removed,
            },
            status=status_code,
        )


@method_decorator(csrf_exempt, name='dispatch')
class LegacyDeviceRegisterView(APIView):
    """Backward-compatible wrapper for the old /api/devices/register/ endpoint."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = {
            'user_id': request.data.get('user_id'),
            'fcm_token': request.data.get('device_token') or request.data.get('fcm_token'),
            'platform': request.data.get('platform'),
        }
        token_serializer = PushTokenSerializer(data=payload)
        token_serializer.is_valid(raise_exception=True)
        token = token_serializer.save()

        preference_payload = {
            'user_id': payload['user_id'],
            'severity_filter': AlertPreference.SEVERITY_ORANGE,
            'notifications_enabled': True,
            'selected_municipality': request.data.get('municipality') or None,
            'selected_sensor_ids': request.data.get('sensor_ids') or [],
        }
        preference_serializer = AlertPreferenceSerializer(data=preference_payload)
        preference_serializer.is_valid(raise_exception=True)
        preference_serializer.save()

        return Response(
            {
                'id': token.id,
                'user_id': token.user_id,
                'device_token': token.fcm_token,
                'platform': token.platform,
                'sensor_ids': preference_payload['selected_sensor_ids'],
                'municipality': preference_payload['selected_municipality'] or '',
                'created_at': token.created_at,
                'updated_at': token.updated_at,
            },
            status=status.HTTP_200_OK,
        )


def _test_push_enabled(request) -> bool:
    if os.environ.get('TEST_PUSH_ENABLED', 'false').lower() == 'true':
        return True

    secret = os.environ.get('TEST_PUSH_SECRET', '').strip()
    if secret and request.headers.get('X-Test-Push-Secret') == secret:
        return True

    return False
