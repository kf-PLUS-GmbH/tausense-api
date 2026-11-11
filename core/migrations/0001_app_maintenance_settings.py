from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AppMaintenanceSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'enabled',
                    models.BooleanField(
                        default=False,
                        help_text='When on, the app shows the maintenance banner (subject to schedule below).',
                    ),
                ),
                (
                    'title',
                    models.CharField(
                        default='Wartungsarbeiten',
                        help_text='Short headline in the app (e.g. “App in Wartung”).',
                        max_length=120,
                    ),
                ),
                (
                    'message',
                    models.TextField(
                        blank=True,
                        help_text='Longer explanation for users (German).',
                    ),
                ),
                (
                    'starts_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='Optional: banner becomes active from this time (UTC stored, shown local in API).',
                        null=True,
                    ),
                ),
                (
                    'ends_at',
                    models.DateTimeField(
                        blank=True,
                        help_text='Optional: banner ends after this time; leave empty for open-ended.',
                        null=True,
                    ),
                ),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'App-Wartungshinweis',
                'verbose_name_plural': 'App-Wartungshinweis',
            },
        ),
    ]
