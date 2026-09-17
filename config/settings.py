"""
Django settings for Taupunktsensorik-App backend.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.database import build_database_config, get_release_mode, load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR)
RELEASE_MODE = get_release_mode()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

SECRET_KEY = os.environ.get('SECRET_KEY', '').strip()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'SECRET_KEY is missing. Add it to your .env file. '
        'Generate one with: python -c "from django.core.management.utils import '
        'get_random_secret_key; print(get_random_secret_key())"'
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', str(RELEASE_MODE != 'release')).lower() == 'true'

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [
        host.strip()
        for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
        if host.strip()
    ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'django_filters',
    'core',
    'municipalities',
    'sensors',
    'readings',
    'alerts',
    'devices.apps.DevicesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database — selected by RELEASE_MODE in .env (dev_local | testing | release)
DATABASES = build_database_config(RELEASE_MODE)


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Taupunktsensorik API',
    'DESCRIPTION': (
        'API-first backend for sensor data in Landkreis Hof municipalities. '
        'Designed for Flutter client generation from OpenAPI.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
}

WEBHOOK_AUTO_CREATE_SENSOR = os.environ.get('WEBHOOK_AUTO_CREATE_SENSOR', 'true').lower() == 'true'
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '').strip()
if RELEASE_MODE in ('release', 'testing') and not WEBHOOK_SECRET:
    raise ImproperlyConfigured(
        'WEBHOOK_SECRET is required when RELEASE_MODE is release or testing. '
        'Set a strong secret in .env and configure the LoRaWAN integration to send '
        'Authorization: Bearer <WEBHOOK_SECRET>.'
    )

FIREBASE_ENABLED = os.environ.get('FIREBASE_ENABLED', 'true').lower() == 'true'
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON', '').strip()
FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', '').strip()
TEST_PUSH_ENABLED = os.environ.get('TEST_PUSH_ENABLED', 'false').lower() == 'true'
TEST_PUSH_SECRET = os.environ.get('TEST_PUSH_SECRET', '').strip()
PUSH_REMINDER_MINUTES = int(os.environ.get('PUSH_REMINDER_MINUTES', '30'))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'devices': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
