import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DevicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'devices'

    def ready(self):
        from devices.firebase_app import initialize_firebase

        try:
            initialize_firebase()
        except Exception:
            logger.exception('Firebase initialization failed during app startup.')
