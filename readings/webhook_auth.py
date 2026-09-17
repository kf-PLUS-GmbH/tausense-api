import secrets

from django.conf import settings


def webhook_bearer_token(request) -> str:
    auth = request.headers.get('Authorization', '')
    prefix = 'Bearer '
    if not auth.startswith(prefix):
        return ''
    return auth[len(prefix):].strip()


def is_webhook_request_authorized(request) -> bool:
    expected = getattr(settings, 'WEBHOOK_SECRET', '')
    if not expected:
        return True
    token = webhook_bearer_token(request)
    if not token:
        return False
    return secrets.compare_digest(token, expected)
