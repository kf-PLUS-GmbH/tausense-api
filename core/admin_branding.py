from django.core.exceptions import PermissionDenied
from django.urls import resolve, Resolver404

from core.roles import HIDDEN_ADMIN_APPS_FOR_STAFF, user_has_write_access

# POST allowed for read-only staff (logout, own password change)
READONLY_POST_URL_NAMES = frozenset(
    {
        'logout',
        'password_change',
        'password_change_done',
    }
)


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

    def readonly_post_allowed(request) -> bool:
        try:
            match = resolve(request.path)
        except Resolver404:
            return False
        return match.url_name in READONLY_POST_URL_NAMES

    original_admin_view = admin_site.admin_view

    def admin_view(view, cacheable=False):
        def wrapped(request, *args, **kwargs):
            if (
                request.method == 'POST'
                and request.user.is_authenticated
                and request.user.is_staff
                and not user_has_write_access(request.user)
                and not readonly_post_allowed(request)
            ):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return original_admin_view(wrapped, cacheable)

    admin_site.admin_view = admin_view
