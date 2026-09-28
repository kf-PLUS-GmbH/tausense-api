from django.core.exceptions import PermissionDenied

from core.roles import HIDDEN_ADMIN_APPS_FOR_STAFF, user_has_write_access


def apply_admin_branding(admin_site) -> None:
    admin_site.site_header = 'TauSense Verwaltung'
    admin_site.site_title = 'TauSense Admin'
    admin_site.index_title = 'Taupunktsensorik · Landkreis Hof'

    original_get_app_list = admin_site.get_app_list

    def get_app_list(request, app_label=None):
        app_list = original_get_app_list(request, app_label=app_label)
        if request.user.is_superuser:
            return app_list
        return [
            app
            for app in app_list
            if app['app_label'] not in HIDDEN_ADMIN_APPS_FOR_STAFF
        ]

    admin_site.get_app_list = get_app_list

    original_admin_view = admin_site.admin_view

    def admin_view(view, cacheable=False):
        def wrapped(request, *args, **kwargs):
            if (
                request.method == 'POST'
                and request.user.is_authenticated
                and request.user.is_staff
                and not user_has_write_access(request.user)
            ):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return original_admin_view(wrapped, cacheable)

    admin_site.admin_view = admin_view
