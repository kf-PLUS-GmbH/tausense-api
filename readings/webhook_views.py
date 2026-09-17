import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from readings.permissions import WebhookSecretPermission
from readings.services.ingestion import WebhookIngestionError, ingest_lorawan_payload
from readings.services.webhook_debug import format_payload_for_log, summarize_webhook_payload
from readings.services.webhook_normalize import (
    normalize_incoming_webhook_payload,
    should_ignore_webhook_event,
)

logger = logging.getLogger('readings.webhook')
from readings.webhook_serializers import (
    LorawanWebhookPayloadSerializer,
    WebhookBulkIngestResponseSerializer,
    WebhookIngestResponseSerializer,
)


@method_decorator(csrf_exempt, name='dispatch')
class LorawanWebhookView(APIView):
    """
    Receives LoRaWAN sensor payloads and persists them as SensorReading rows.
    """

    permission_classes = [WebhookSecretPermission]
    authentication_classes = []

    def _normalize_payload(self, data):
        if isinstance(data, list):
            return data, True
        return [data], False

    def _log_incoming(self, event, raw_item, normalized, *, outcome: str, extra: str = ''):
        summary = summarize_webhook_payload(raw_item)
        normalized_keys = sorted(normalized.keys()) if isinstance(normalized, dict) else []
        msg = (
            f'webhook {outcome} event={event!r} summary={summary} '
            f'normalized_keys={normalized_keys}'
        )
        if extra:
            msg = f'{msg} {extra}'
        if getattr(settings, 'WEBHOOK_LOG_PAYLOAD', False):
            msg = f'{msg} body={format_payload_for_log(raw_item)}'
        if outcome == 'rejected':
            logger.warning(msg)
        else:
            logger.info(msg)

    def _response_item(self, reading) -> dict:
        return {
            'status': 'ok',
            'reading_id': reading.id,
            'sensor_id': reading.sensor_id,
            'external_id': reading.sensor.external_id,
            'device_name': reading.device_name,
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
            'Unknown sensors are auto-created without municipality when WEBHOOK_AUTO_CREATE_SENSOR=true. '
            'When WEBHOOK_SECRET is set, send header Authorization: Bearer <WEBHOOK_SECRET>.'
        ),
    )
    def post(self, request):
        event = request.query_params.get('event')
        if should_ignore_webhook_event(event):
            return Response(
                {'status': 'ignored', 'event': event},
                status=status.HTTP_200_OK,
            )

        payloads, is_bulk = self._normalize_payload(request.data)
        if not payloads:
            return Response({'detail': 'Request body must be a JSON object or array.'}, status=400)

        results = []
        for index, item in enumerate(payloads):
            if not isinstance(item, dict):
                return Response(
                    {
                        'detail': 'Each payload entry must be a JSON object.',
                        'index': index,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raw_item = item
            normalized = normalize_incoming_webhook_payload(raw_item)
            serializer = LorawanWebhookPayloadSerializer(data=normalized)
            if not serializer.is_valid():
                self._log_incoming(
                    event,
                    raw_item,
                    normalized,
                    outcome='rejected',
                    extra=f'validation_errors={serializer.errors}',
                )
                return Response(
                    {'detail': 'Validation failed.', 'index': index, 'errors': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                reading = ingest_lorawan_payload(normalized, raw_payload=raw_item)
            except WebhookIngestionError as exc:
                self._log_incoming(
                    event,
                    raw_item,
                    normalized,
                    outcome='rejected',
                    extra=f'ingestion_error={exc.message!r} field={exc.field!r}',
                )
                body = {'detail': exc.message}
                if exc.field:
                    body['field'] = exc.field
                if is_bulk:
                    body['index'] = index
                return Response(body, status=status.HTTP_400_BAD_REQUEST)

            self._log_incoming(event, raw_item, normalized, outcome='accepted')
            results.append(self._response_item(reading))

        if is_bulk:
            return Response(
                {'status': 'ok', 'count': len(results), 'results': results},
                status=status.HTTP_201_CREATED,
            )
        return Response(results[0], status=status.HTTP_201_CREATED)
