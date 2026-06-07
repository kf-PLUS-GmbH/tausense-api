from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from readings.services.ingestion import WebhookIngestionError, ingest_lorawan_payload
from readings.webhook_serializers import (
    LorawanWebhookPayloadSerializer,
    WebhookBulkIngestResponseSerializer,
    WebhookIngestResponseSerializer,
)


class LorawanWebhookView(APIView):
    """
    Receives LoRaWAN sensor payloads and persists them as SensorReading rows.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def _check_secret(self, request) -> Response | None:
        expected = getattr(settings, 'WEBHOOK_SECRET', '') or ''
        if not expected:
            return None
        provided = request.headers.get('X-Webhook-Secret', '')
        if provided != expected:
            return Response({'detail': 'Invalid webhook secret.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _normalize_payload(self, data):
        if isinstance(data, list):
            return data, True
        return [data], False

    def _response_item(self, reading) -> dict:
        return {
            'status': 'ok',
            'reading_id': reading.id,
            'sensor_id': reading.sensor_id,
            'external_id': reading.sensor.external_id,
            'timestamp': reading.timestamp,
        }

    @extend_schema(
        tags=['Webhook'],
        request=LorawanWebhookPayloadSerializer,
        responses={201: WebhookIngestResponseSerializer},
        examples=[
            OpenApiExample(
                'LoRaWAN payload',
                value={
                    'rxTime': '2026-06-03T09:10:05.743Z',
                    'deviceEui': '70B3D57BA000638D',
                    'deviceName': 'MUB-TPK-0001-N50.22764-E11.76708',
                    'air_temperature_radiation_shield': 12.84,
                    'air_humidity_radiation_shield': 83.77,
                    'surface_temperature': 24.8,
                    'air_temperature': 14.53,
                    'air_humidity': 73.64,
                    'dew_point': 9.89,
                    'lat': 50.22764,
                    'lon': 11.76708,
                    'timestamp': '2026-06-03T09:10:06.316Z',
                },
                request_only=True,
            )
        ],
        description=(
            'Ingest LoRaWAN sensor data into PostgreSQL. '
            'Maps deviceEui to Sensor.external_id and stores a SensorReading. '
            'Unknown sensors are auto-created without municipality when WEBHOOK_AUTO_CREATE_SENSOR=true.'
        ),
    )
    def post(self, request):
        denied = self._check_secret(request)
        if denied is not None:
            return denied

        payloads, is_bulk = self._normalize_payload(request.data)
        if not payloads:
            return Response({'detail': 'Request body must be a JSON object or array.'}, status=400)

        results = []
        for index, item in enumerate(payloads):
            serializer = LorawanWebhookPayloadSerializer(data=item)
            if not serializer.is_valid():
                return Response(
                    {'detail': 'Validation failed.', 'index': index, 'errors': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                reading = ingest_lorawan_payload(item)
            except WebhookIngestionError as exc:
                body = {'detail': exc.message}
                if exc.field:
                    body['field'] = exc.field
                if is_bulk:
                    body['index'] = index
                return Response(body, status=status.HTTP_400_BAD_REQUEST)

            results.append(self._response_item(reading))

        if is_bulk:
            return Response(
                {'status': 'ok', 'count': len(results), 'results': results},
                status=status.HTTP_201_CREATED,
            )
        return Response(results[0], status=status.HTTP_201_CREATED)
