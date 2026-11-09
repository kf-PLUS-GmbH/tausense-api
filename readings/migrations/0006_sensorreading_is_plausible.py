from django.db import migrations, models


def backfill_is_plausible(apps, schema_editor):
    from django.conf import settings

    cfg = getattr(settings, 'READING_PLAUSIBILITY', {})
    limits = (
        float(cfg.get('road_temp_min', -50.0)),
        float(cfg.get('road_temp_max', 60.0)),
        float(cfg.get('air_temp_min', -50.0)),
        float(cfg.get('air_temp_max', 50.0)),
        float(cfg.get('humidity_min', 0.0)),
        float(cfg.get('humidity_max', 100.0)),
    )
    SensorReading = apps.get_model('readings', 'SensorReading')
    table = SensorReading._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {table}
            SET is_plausible = FALSE
            WHERE road_temperature < %s OR road_temperature > %s
               OR air_temperature < %s OR air_temperature > %s
               OR humidity < %s OR humidity > %s
            """,
            limits,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('readings', '0005_add_device_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensorreading',
            name='is_plausible',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='False when values are outside configured physical limits (still stored for diagnostics).',
            ),
        ),
        migrations.RunPython(backfill_is_plausible, migrations.RunPython.noop),
    ]
