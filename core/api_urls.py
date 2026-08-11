from django.urls import include, path
from rest_framework.routers import DefaultRouter

from alerts.views import AlertEventViewSet, AlertRuleViewSet
from core.views import (
    DashboardColdestSensorView,
    DashboardMapDataView,
    DashboardWarningsView,
)
from devices.views import AlertPreferencesView, PushTokenView
from municipalities.views import MunicipalityViewSet
from readings.views import SensorReadingViewSet
from sensors.views import SensorViewSet

router = DefaultRouter()
router.register(r'sensors', SensorViewSet, basename='sensor')
router.register(r'readings', SensorReadingViewSet, basename='reading')
router.register(r'municipalities', MunicipalityViewSet, basename='municipality')
router.register(r'alerts/rules', AlertRuleViewSet, basename='alert-rule')
router.register(r'alerts/events', AlertEventViewSet, basename='alert-event')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/warnings/', DashboardWarningsView.as_view(), name='dashboard-warnings'),
    path(
        'dashboard/coldest-sensor/',
        DashboardColdestSensorView.as_view(),
        name='dashboard-coldest-sensor',
    ),
    path('dashboard/map-data/', DashboardMapDataView.as_view(), name='dashboard-map-data'),
    path('alerts/preferences/', AlertPreferencesView.as_view(), name='alert-preferences'),
    path('push-tokens/', PushTokenView.as_view(), name='push-tokens'),
]
