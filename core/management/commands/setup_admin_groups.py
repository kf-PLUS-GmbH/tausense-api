from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.roles import (
    GROUP_ADMIN,
    GROUP_VIEWER,
    ensure_admin_groups,
    user_has_write_access,
)


class Command(BaseCommand):
    help = (
        'Create TauSense Admin / TauSense Viewer groups and assign model permissions.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--promote',
            metavar='USERNAME',
            help=f'Add user to {GROUP_ADMIN} (must exist, is_staff recommended).',
        )
        parser.add_argument(
            '--viewer',
            metavar='USERNAME',
            help=f'Add user to {GROUP_VIEWER} (read-only admin).',
        )
        parser.add_argument(
            '--inspect',
            metavar='USERNAME',
            help='Show staff flags and groups for a user.',
        )

    def handle(self, *args, **options):
        inspect_name = options.get('inspect')
        if inspect_name:
            try:
                user = User.objects.get(username=inspect_name)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'User not found: {inspect_name}'))
                return
            groups = ', '.join(user.groups.values_list('name', flat=True)) or '(none)'
            self.stdout.write(f'User: {user.username}')
            self.stdout.write(f'  is_staff={user.is_staff} is_superuser={user.is_superuser}')
            self.stdout.write(f'  groups: {groups}')
            self.stdout.write(
                f'  admin write access: {user_has_write_access(user)}'
            )
            return

        admin_group, viewer_group = ensure_admin_groups()
        self.stdout.write(
            self.style.SUCCESS(
                f'Groups ready: «{GROUP_ADMIN}» ({admin_group.permissions.count()} '
                f'permissions), «{GROUP_VIEWER}» '
                f'({viewer_group.permissions.count()} view permissions).'
            )
        )

        for flag, group, label in (
            ('promote', admin_group, GROUP_ADMIN),
            ('viewer', viewer_group, GROUP_VIEWER),
        ):
            username = options.get(flag)
            if not username:
                continue
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f'User not found: {username}')
                )
                continue
            user.is_staff = True
            if flag == 'viewer':
                user.is_superuser = False
                user.groups.remove(admin_group)
                user.save(update_fields=['is_staff', 'is_superuser'])
                user.groups.add(viewer_group)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{username} → {GROUP_VIEWER} '
                        f'(is_staff=True, is_superuser=False)'
                    )
                )
                continue
            user.groups.remove(viewer_group)
            user.save(update_fields=['is_staff'])
            user.groups.add(admin_group)
            self.stdout.write(
                self.style.SUCCESS(f'{username} → {GROUP_ADMIN} (is_staff=True)')
            )

        self.stdout.write(
            'Create users: python manage.py createsuperuser '
            'or Django admin (superuser only).'
        )
