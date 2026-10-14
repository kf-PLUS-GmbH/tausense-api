from django.test import SimpleTestCase

from core.query_profiling import profile_callable


class QueryProfilingTests(SimpleTestCase):
    def test_profile_callable_records_timing(self):
        def sample():
            return [1, 2, 3]

        profile = profile_callable('sample', sample)
        self.assertGreaterEqual(profile.duration_ms, 0)
        self.assertEqual(profile.result_summary['count'], 3)
