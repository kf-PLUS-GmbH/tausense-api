from django.contrib import admin
from django.shortcuts import render
from django.urls import path

from core.performance_benchmarks import BENCHMARK_CHOICES, run_benchmark
from core.roles import user_has_write_access


def performance_dashboard_view(request):
    if not request.user.is_staff:
        return admin.site.login(request)

    profiles = []
    error = None
    selected = request.POST.get('benchmark') if request.method == 'POST' else 'map_data'

    if request.method == 'POST' and not user_has_write_access(request.user):
        error = 'Nur TauSense Admin oder Superuser dürfen Benchmarks ausführen.'
    elif request.method == 'POST':
        try:
            if selected == 'run_all':
                for benchmark_id, _label in BENCHMARK_CHOICES:
                    if benchmark_id == 'map_data_breakdown':
                        continue
                    profiles.append(run_benchmark(benchmark_id))
            else:
                profiles.append(run_benchmark(selected))
        except Exception as exc:
            error = str(exc)

    context = {
        **admin.site.each_context(request),
        'title': 'Performance-Diagnose',
        'profiles': profiles,
        'benchmark_choices': BENCHMARK_CHOICES,
        'selected': selected,
        'error': error,
        'can_run': user_has_write_access(request.user),
    }
    return render(request, 'admin/core/performance_dashboard.html', context)


def register_performance_admin_urls():
    original_get_urls = admin.site.get_urls

    def get_urls():
        custom = [
            path(
                'core/performance/',
                admin.site.admin_view(performance_dashboard_view),
                name='core_performance_dashboard',
            ),
        ]
        return custom + original_get_urls()

    admin.site.get_urls = get_urls
