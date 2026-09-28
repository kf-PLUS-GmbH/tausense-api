"""Admin role groups for Django staff users."""

from django.contrib.auth.models import Group, Permission

GROUP_ADMIN = 'TauSense Admin'
GROUP_VIEWER = 'TauSense Viewer'

TAUSENSE_APP_LABELS = (
    'sensors',
    'readings',
    'municipalities',
    'alerts',
    'devices',
)

HIDDEN_ADMIN_APPS_FOR_STAFF = (
    'auth',
    'contenttypes',
    'sessions',
    'admin',
)


def tausense_permissions():
    return Permission.objects.filter(
        content_type__app_label__in=TAUSENSE_APP_LABELS,
    )


def ensure_admin_groups() -> tuple[Group, Group]:
    admin_group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
    viewer_group, _ = Group.objects.get_or_create(name=GROUP_VIEWER)

    all_perms = tausense_permissions()
    admin_group.permissions.set(all_perms)
    viewer_group.permissions.set(all_perms.filter(codename__startswith='view_'))

    return admin_group, viewer_group


def user_is_viewer(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return False
    return user.groups.filter(name=GROUP_VIEWER).exists()


def user_is_tausense_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=GROUP_ADMIN).exists()


def user_has_write_access(user) -> bool:
    if not user.is_authenticated or not user.is_staff:
        return False
    if user.is_superuser or user_is_tausense_admin(user):
        return True
    return not user_is_viewer(user)
