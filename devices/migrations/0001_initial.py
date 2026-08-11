from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, max_length=255)),
                ('fcm_token', models.CharField(max_length=512, unique=True)),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS')], max_length=20)),
                (
                    'sensor_ids',
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='List of subscribed sensor primary keys.',
                    ),
                ),
                (
                    'municipality',
                    models.CharField(
                        blank=True,
                        help_text='Municipality name for municipality-wide subscriptions.',
                        max_length=255,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'device_tokens',
                'ordering': ['-updated_at'],
                'indexes': [
                    models.Index(fields=['user_id'], name='device_toke_user_id_0f8f0d_idx'),
                    models.Index(fields=['municipality'], name='device_toke_municip_8a0d0b_idx'),
                ],
            },
        ),
    ]
