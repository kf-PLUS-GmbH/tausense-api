from core.roles import HIDDEN_ADMIN_APPS_FOR_STAFF


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
