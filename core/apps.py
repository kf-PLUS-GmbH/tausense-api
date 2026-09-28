from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from django.contrib import admin

        from core.admin_branding import apply_admin_branding

        apply_admin_branding(admin.site)
