from django.test import TestCase
from rest_framework.test import APIClient

from municipalities.models import Municipality


class MunicipalityBoundaryApiTests(TestCase):
    def setUp(self):
        Municipality.objects.create(
            name='Hof',
            geo_boundary={
                'type': 'Polygon',
                'coordinates': [
                    [
                        [11.9, 50.28],
                        [11.98, 50.28],
                        [11.98, 50.34],
                        [11.9, 50.28],
                    ]
                ],
            },
        )

    def test_list_returns_geo_boundary(self):
        response = APIClient().get('/api/v1/municipalities/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Hof')
        self.assertEqual(response.data[0]['geo_boundary']['type'], 'Polygon')

    def test_filter_by_name(self):
        response = APIClient().get('/api/v1/municipalities/', {'name': 'hof'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Hof')
