from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sensors', '0006_sensor_ice_warning_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='maintenance_mode',
            field=models.BooleanField(
                default=False,
                help_text='When set, the app shows maintenance status and hides live warning colours.',
            ),
        ),
    ]
