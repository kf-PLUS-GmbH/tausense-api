from django.db import migrations, models

import devices.notification_schedule


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0005_push_digest_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='alertpreference',
            name='notification_schedule',
            field=models.JSONField(
                blank=True,
                default=devices.notification_schedule.default_notification_schedule,
            ),
        ),
    ]
