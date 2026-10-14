from django.core.management.base import BaseCommand

from core.performance_benchmarks import BENCHMARK_CHOICES, run_benchmark


class Command(BaseCommand):
    help = 'Profile dashboard API service functions (SQL count and timings).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--benchmark',
            choices=[key for key, _ in BENCHMARK_CHOICES] + ['all'],
            default='map_data',
        )

    def handle(self, *args, **options):
        benchmark = options['benchmark']
        keys = [key for key, _ in BENCHMARK_CHOICES]
        if benchmark == 'all':
            keys = [k for k in keys if k != 'map_data_breakdown']

        for key in keys if benchmark == 'all' else [benchmark]:
            profile = run_benchmark(key)
            self.stdout.write(self.style.MIGRATE_HEADING(profile.label))
            self.stdout.write(
                f'  total={profile.duration_ms:.1f} ms  '
                f'queries={profile.query_count}  '
                f'db={profile.db_time_ms:.1f} ms  '
                f'result={profile.result_summary}',
            )
            for query in profile.slow_queries[:5]:
                self.stdout.write(
                    f'    - {query.duration_ms:.2f} ms: {query.sql[:160]}...',
                )
