from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.roles import GROUP_ADMIN, GROUP_VIEWER, ensure_admin_groups


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

    def handle(self, *args, **options):
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
            user.save(update_fields=['is_staff'])
            user.groups.add(group)
            self.stdout.write(
                self.style.SUCCESS(f'{username} → {label} (is_staff=True)')
            )

        self.stdout.write(
            'Create users: python manage.py createsuperuser '
            'or Django admin (superuser only).'
        )
