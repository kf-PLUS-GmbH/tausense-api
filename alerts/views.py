from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets

from alerts.models import AlertEvent, AlertRule
from alerts.serializers import AlertEventSerializer, AlertRuleSerializer


@extend_schema(tags=['Alerts'])
class AlertRuleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AlertRule.objects.select_related('sensor', 'municipality').all()
    serializer_class = AlertRuleSerializer


@extend_schema(tags=['Alerts'])
class AlertEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AlertEvent.objects.select_related('rule', 'sensor').all()
    serializer_class = AlertEventSerializer
