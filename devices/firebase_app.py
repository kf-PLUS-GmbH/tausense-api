import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_credentials_path(file_path: str) -> str:
    path = Path(file_path)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / path).resolve())


def initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK from environment variables.

    Supports either:
    - FIREBASE_SERVICE_ACCOUNT_JSON: JSON string of the service account
    - FIREBASE_SERVICE_ACCOUNT_PATH: path to the service account JSON file
    """
    if not _firebase_enabled():
        logger.info('Firebase push notifications are disabled (FIREBASE_ENABLED=false).')
        return False

    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return True

    json_payload = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON', '').strip()
    file_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', '').strip()

    if not json_payload and not file_path:
        logger.warning(
            'Firebase credentials are missing. Set FIREBASE_SERVICE_ACCOUNT_JSON or '
            'FIREBASE_SERVICE_ACCOUNT_PATH to enable push notifications.'
        )
        return False

    try:
        if json_payload:
            service_account = json.loads(json_payload)
            cred = credentials.Certificate(service_account)
        else:
            cred = credentials.Certificate(_resolve_credentials_path(file_path))

        firebase_admin.initialize_app(cred)
        logger.info('Firebase Admin SDK initialized successfully.')
        return True
    except json.JSONDecodeError:
        logger.exception('FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON.')
        return False
    except Exception:
        logger.exception('Failed to initialize Firebase Admin SDK.')
        return False


def is_firebase_ready() -> bool:
    if not _firebase_enabled():
        return False

    import firebase_admin

    return bool(firebase_admin._apps)


def _firebase_enabled() -> bool:
    return os.environ.get('FIREBASE_ENABLED', 'true').lower() == 'true'
