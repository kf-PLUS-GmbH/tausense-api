import logging
import time

from django.db import close_old_connections
from django.utils.deprecation import MiddlewareMixin

from core.query_profiling import QueryProfiler

logger = logging.getLogger('core.performance')


class CloseDbConnectionMiddleware(MiddlewareMixin):
    """Release the DB connection after each request (important with runserver/threading)."""

    def process_response(self, request, response):
        close_old_connections()
        return response

    def process_exception(self, request, exception):
        close_old_connections()
        return None


class StaffApiProfilingMiddleware(MiddlewareMixin):
    """
    Optional live profiling for staff users:
    GET /api/v1/...?profile=1  (must be logged into Django admin in same browser)
    Adds X-Request-Duration-Ms, X-Query-Count, X-Query-Time-Ms response headers.
    """

    def process_request(self, request):
        if not self._should_profile(request):
            request._query_profiler = None
            request._profile_started = None
            return None
        request._profile_started = time.perf_counter()
        request._query_profiler = QueryProfiler()
        request._query_profiler.__enter__()
        return None

    def process_response(self, request, response):
        profiler = getattr(request, '_query_profiler', None)
        started = getattr(request, '_profile_started', None)
        if profiler is None or started is None:
            return response
        try:
            duration_ms = (time.perf_counter() - started) * 1000
            response['X-Request-Duration-Ms'] = f'{duration_ms:.2f}'
            response['X-Query-Count'] = str(profiler.query_count)
            response['X-Query-Time-Ms'] = f'{profiler.db_time_ms:.2f}'
            logger.info(
                'Staff profile %s %s -> %s ms, %s queries (%s ms SQL)',
                request.method,
                request.path,
                f'{duration_ms:.1f}',
                profiler.query_count,
                f'{profiler.db_time_ms:.1f}',
            )
        finally:
            profiler.__exit__(None, None, None)
        return response

    def _should_profile(self, request) -> bool:
        if request.method != 'GET':
            return False
        if request.GET.get('profile') != '1':
            return False
        if not request.path.startswith('/api/v1/'):
            return False
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and user.is_staff)
