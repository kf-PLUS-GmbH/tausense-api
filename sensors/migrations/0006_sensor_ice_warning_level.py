from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sensors', '0005_add_sensor_timestamps'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='ice_warning_level',
            field=models.CharField(
                choices=[
                    ('none', 'none'),
                    ('possible_slip', 'possible_slip'),
                    ('increased_ice', 'increased_ice'),
                    ('acute_ice', 'acute_ice'),
                ],
                db_index=True,
                default='none',
                help_text='Aktive Warnstufe inkl. Reset-Hysterese und Verifikationszeit.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='sensor',
            name='ice_warning_level_since',
            field=models.DateTimeField(
                blank=True,
                help_text='Zeitpunkt der letzten Änderung der aktiven Warnstufe.',
                null=True,
            ),
        ),
    ]
