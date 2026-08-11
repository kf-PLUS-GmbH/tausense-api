from django.db import migrations, models


def migrate_device_tokens(apps, schema_editor):
    DeviceToken = apps.get_model('devices', 'DeviceToken')
    PushToken = apps.get_model('devices', 'PushToken')
    AlertPreference = apps.get_model('devices', 'AlertPreference')

    for device in DeviceToken.objects.all().order_by('id'):
        PushToken.objects.update_or_create(
            fcm_token=device.fcm_token,
            defaults={
                'user_id': device.user_id,
                'platform': device.platform,
                'created_at': device.created_at,
                'updated_at': device.updated_at,
            },
        )
        AlertPreference.objects.update_or_create(
            user_id=device.user_id,
            defaults={
                'severity_filter': 'orange',
                'notifications_enabled': True,
                'selected_municipality': device.municipality or None,
                'selected_sensor_ids': device.sensor_ids or [],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0002_rename_device_toke_user_id_0f8f0d_idx_device_toke_user_id_25a987_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('severity_filter', models.CharField(choices=[('orange', 'Orange and red'), ('red', 'Red only')], max_length=10)),
                ('notifications_enabled', models.BooleanField(default=True)),
                ('selected_municipality', models.CharField(blank=True, max_length=255, null=True)),
                ('selected_sensor_ids', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='PushToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, max_length=255)),
                ('fcm_token', models.CharField(max_length=512, unique=True)),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'push_tokens',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.RunPython(migrate_device_tokens, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='DeviceToken',
        ),
        migrations.AddIndex(
            model_name='pushtoken',
            index=models.Index(fields=['user_id'], name='push_tokens_user_id_21a6ab_idx'),
        ),
    ]
