from rest_framework.permissions import BasePermission

from readings.webhook_auth import is_webhook_request_authorized


class WebhookSecretPermission(BasePermission):
    message = 'Invalid or missing Authorization Bearer token for webhook.'

    def has_permission(self, request, view):
        return is_webhook_request_authorized(request)
