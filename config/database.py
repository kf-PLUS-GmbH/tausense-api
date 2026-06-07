import os

from django.core.exceptions import ImproperlyConfigured

RELEASE_MODES = {
    'dev_local': 'DEV_LOCAL',
    'testing': 'TESTING',
    'release': 'RELEASE',
}


def load_dotenv(base_dir) -> None:
    env_path = base_dir / '.env'
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        return
    _load(env_path)


def get_release_mode() -> str:
    mode = os.environ.get('RELEASE_MODE', '').strip().lower()
    if not mode:
        if os.environ.get('POSTGRES_DB') or os.environ.get('POSTGRES_DB_TESTING'):
            return 'testing'
        return 'dev_local'
    if mode not in RELEASE_MODES:
        raise ImproperlyConfigured(
            f'Invalid RELEASE_MODE="{mode}". '
            f'Use one of: {", ".join(RELEASE_MODES)}.'
        )
    return mode


def _postgres_value(key: str, prefix: str) -> str | None:
    suffixed = os.environ.get(f'POSTGRES_{key}_{prefix}')
    if suffixed:
        return suffixed
    if prefix == 'TESTING':
        return os.environ.get(f'POSTGRES_{key}')
    return None


def build_database_config(release_mode: str) -> dict:
    prefix = RELEASE_MODES[release_mode]
    name = _postgres_value('DB', prefix)
    user = _postgres_value('USER', prefix)
    password = _postgres_value('PASSWORD', prefix)
    host = _postgres_value('HOST', prefix)
    port = _postgres_value('PORT', prefix)

    missing = [
        label
        for label, value in (
            ('DB', name),
            ('USER', user),
            ('PASSWORD', password),
            ('HOST', host),
        )
        if not value
    ]
    if missing:
        raise ImproperlyConfigured(
            f'RELEASE_MODE={release_mode} requires PostgreSQL variables: '
            f'{", ".join(f"POSTGRES_{key}_{prefix}" for key in missing)} '
            f'(legacy POSTGRES_* without suffix is supported for testing).'
        )

    return {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': name,
            'USER': user,
            'PASSWORD': password,
            'HOST': host,
            'PORT': port or '5432',
        }
    }
