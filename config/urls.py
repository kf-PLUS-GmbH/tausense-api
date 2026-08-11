from django.contrib import admin
from django.urls import include, path

from readings.webhook_views import LorawanWebhookView
from devices.views import AlertPreferencesView, LegacyDeviceRegisterView, PushTokenView, TestPushView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/swagger/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/docs/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    path('api/webhook/', LorawanWebhookView.as_view(), name='lorawan-webhook'),
    path('api/devices/register/', LegacyDeviceRegisterView.as_view(), name='device-register'),
    path('api/test/push/', TestPushView.as_view(), name='test-push'),
    path('api/v1/', include('core.api_urls')),
]
