import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from sensors.models import Sensor


class ImportSensorMetadataTests(TestCase):
    def test_upsert_preserves_external_id(self):
        Sensor.objects.create(
            name='Old label',
            device_name='TST-TPK-0001-N50.1-E11.2',
            external_id='eui-deadbeef',
            sensor_type=Sensor.TYPE_STANDARD,
            operator_name='Old Kommune',
        )

        csv_body = (
            'Standortbezeichnung,Kommune,Name,Standort (Adresse),'
            'Standort (GPS/ W3W)\n'
            'TST-TPK-0001-N50.1-E11.2,Neue Kommune,Neuer Name,'
            'Neue Adresse,50.1, 11.2\n'
        )
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False,
            encoding='utf-8',
            newline='',
        ) as handle:
            handle.write(csv_body)
            path = handle.name

        try:
            call_command('import_sensor_metadata', path, stdout=StringIO())
        finally:
            Path(path).unlink(missing_ok=True)

        sensor = Sensor.objects.get(device_name='TST-TPK-0001-N50.1-E11.2')
        self.assertEqual(sensor.external_id, 'eui-deadbeef')
        self.assertEqual(sensor.operator_name, 'Neue Kommune')
        self.assertEqual(sensor.display_name, 'Neuer Name')
        self.assertEqual(Sensor.objects.count(), 1)

    def test_creates_new_and_updates_existing(self):
        Sensor.objects.create(
            name='Existing',
            device_name='TST-TPK-0002-N50.2-E11.3',
            sensor_type=Sensor.TYPE_STANDARD,
        )

        csv_body = (
            'Standortbezeichnung,Kommune,Name,Standort (Adresse),'
            'Standort (GPS/ W3W)\n'
            'TST-TPK-0002-N50.2-E11.3,Hof,Updated,,50.2, 11.3\n'
            'TST-TPK-0003-N50.3-E11.4,Hof,Brand New,,50.3, 11.4\n'
        )
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False,
            encoding='utf-8',
            newline='',
        ) as handle:
            handle.write(csv_body)
            path = handle.name

        try:
            out = StringIO()
            call_command('import_sensor_metadata', path, stdout=out)
            summary = out.getvalue()
        finally:
            Path(path).unlink(missing_ok=True)

        self.assertIn('1 created', summary)
        self.assertIn('1 updated', summary)
        self.assertEqual(Sensor.objects.count(), 2)
