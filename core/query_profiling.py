from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from django.db import connection


@dataclass
class QueryRecord:
    sql: str
    duration_ms: float


@dataclass
class StepProfile:
    name: str
    duration_ms: float
    query_count: int
    db_time_ms: float
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestProfile:
    label: str
    duration_ms: float
    query_count: int
    db_time_ms: float
    queries: list[QueryRecord]
    steps: list[StepProfile] = field(default_factory=list)
    result_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_query_ms(self) -> float:
        if self.query_count <= 0:
            return 0.0
        return self.db_time_ms / self.query_count

    @property
    def slow_queries(self) -> list[QueryRecord]:
        return sorted(self.queries, key=lambda item: item.duration_ms, reverse=True)[:12]


class QueryProfiler:
    """Records SQL timings via Django execute_wrapper (works with DEBUG=False)."""

    def __init__(self) -> None:
        self.queries: list[QueryRecord] = []
        self._cm = None

    def __enter__(self) -> QueryProfiler:
        profiler = self

        def wrapper(execute, sql, params, many, context):
            start = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                profiler.queries.append(
                    QueryRecord(
                        sql=' '.join(sql.split()),
                        duration_ms=(time.perf_counter() - start) * 1000,
                    ),
                )

        self._cm = connection.execute_wrapper(wrapper)
        self._cm.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._cm is not None:
            self._cm.__exit__(exc_type, exc, tb)

    @property
    def query_count(self) -> int:
        return len(self.queries)

    @property
    def db_time_ms(self) -> float:
        return sum(record.duration_ms for record in self.queries)

    def slowest(self, limit: int = 15) -> list[QueryRecord]:
        return sorted(self.queries, key=lambda item: item.duration_ms, reverse=True)[:limit]


def profile_callable(label: str, func: Callable, *args, **kwargs) -> RequestProfile:
    started = time.perf_counter()
    with QueryProfiler() as profiler:
        result = func(*args, **kwargs)
    duration_ms = (time.perf_counter() - started) * 1000
    return RequestProfile(
        label=label,
        duration_ms=duration_ms,
        query_count=profiler.query_count,
        db_time_ms=profiler.db_time_ms,
        queries=profiler.queries,
        result_summary=_summarize_result(result),
    )


def profile_steps(label: str, steps: list[tuple[str, Callable[[], Any]]]) -> RequestProfile:
    started = time.perf_counter()
    step_profiles: list[StepProfile] = []
    last_query_index = 0
    final_result = None

    with QueryProfiler() as profiler:
        for step_name, step_fn in steps:
            step_started = time.perf_counter()
            final_result = step_fn()
            step_queries = profiler.queries[last_query_index:]
            last_query_index = len(profiler.queries)
            step_profiles.append(
                StepProfile(
                    name=step_name,
                    duration_ms=(time.perf_counter() - step_started) * 1000,
                    query_count=len(step_queries),
                    db_time_ms=sum(q.duration_ms for q in step_queries),
                ),
            )

    duration_ms = (time.perf_counter() - started) * 1000
    return RequestProfile(
        label=label,
        duration_ms=duration_ms,
        query_count=profiler.query_count,
        db_time_ms=profiler.db_time_ms,
        queries=profiler.queries,
        steps=step_profiles,
        result_summary=_summarize_result(final_result),
    )


def _summarize_result(result: Any) -> dict[str, Any]:
    if result is None:
        return {'type': 'none'}
    if isinstance(result, list):
        return {'type': 'list', 'count': len(result)}
    if isinstance(result, dict):
        return {'type': 'dict', 'keys': len(result)}
    return {'type': type(result).__name__}
