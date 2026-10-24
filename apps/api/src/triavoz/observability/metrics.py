"""Prometheus metrics for the API. Labels never contain tenant, caller or transcript data.

`/metrics` is scraped by Prometheus; the Grafana dashboard in `infra/observability` uses these
series. Per-clinic business metrics that need history (handoff rate, slot-taken rate, cost per
call/minute) are also persisted in PostgreSQL and exposed by `GET /api/v1/dashboard`.
"""

from __future__ import annotations

from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "triavoz_http_requests_total",
    "HTTP requests handled by the API.",
    ["method", "path", "status"],
)
HTTP_DURATION = Histogram(
    "triavoz_http_request_duration_seconds",
    "HTTP request duration.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
CALLS_STARTED = Counter(
    "triavoz_calls_started_total",
    "Voice calls started (room created).",
    ["channel"],
)
CALLS_ENDED = Counter(
    "triavoz_calls_ended_total",
    "Voice calls finished, by outcome.",
    ["status", "reason"],
)
CALL_DURATION = Histogram(
    "triavoz_call_duration_seconds",
    "Voice call duration.",
    buckets=(5, 15, 30, 60, 120, 180, 300, 600, 1200),
)
CALL_COST = Histogram(
    "triavoz_call_cost_cents",
    "Estimated cost per voice call in cents.",
    buckets=(0.25, 0.5, 1, 2, 3, 5, 10, 25, 50, 100),
)
CALL_MINUTES = Counter(
    "triavoz_call_minutes_total",
    "Total voice minutes processed.",
)
HANDOFFS = Counter(
    "triavoz_handoffs_total",
    "Human handoff requests.",
    ["reason", "completed"],
)
TOOL_CALLS = Counter(
    "triavoz_tool_calls_total",
    "Agent tool calls served by the internal API.",
    ["tool"],
)
TOOL_ERRORS = Counter(
    "triavoz_tool_errors_total",
    "Agent tool calls that returned a domain error.",
    ["tool", "code"],
)
SLOT_TAKEN = Counter(
    "triavoz_slot_taken_total",
    "Booking attempts refused because the slot was no longer free.",
)
GATEKEEPER_BLOCKS = Counter(
    "triavoz_gatekeeper_blocks_total",
    "Voice sessions refused by the gatekeeper (before any provider spend).",
    ["reason"],
)
STAGE_P50 = Histogram(
    "triavoz_stage_p50_ms",
    "Per-call p50 latency of each voice pipeline stage, in milliseconds.",
    ["stage"],
    buckets=(50, 100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000, 10000),
)
STAGE_P95 = Histogram(
    "triavoz_stage_p95_ms",
    "Per-call p95 latency of each voice pipeline stage, in milliseconds.",
    ["stage"],
    buckets=(50, 100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000, 10000),
)


def metrics_payload() -> bytes:
    return generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def observe_http(*, method: str, path: str, status: int, seconds: float) -> None:
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_DURATION.labels(method=method, path=path).observe(max(0.0, seconds))


def observe_call_started(*, channel: str) -> None:
    CALLS_STARTED.labels(channel=channel).inc()


def observe_tool_call(tool: str) -> None:
    TOOL_CALLS.labels(tool=tool).inc()


def observe_tool_error(tool: str, code: str) -> None:
    TOOL_ERRORS.labels(tool=tool, code=code[:80] or "error").inc()
    if code in {"slot_taken", "slot_unavailable"}:
        SLOT_TAKEN.inc()


def observe_gatekeeper_block(reason: str) -> None:
    GATEKEEPER_BLOCKS.labels(reason=reason).inc()


def observe_handoff(reason: str, *, completed: bool) -> None:
    HANDOFFS.labels(reason=reason, completed="true" if completed else "false").inc()


def observe_call_ended(
    *,
    status: str,
    reason: str | None,
    duration_seconds: int | None,
    cost_cents: float,
    handoff_requested: bool,
    latency_ms: dict[str, Any],
    handoff_completed: bool = False,
) -> None:
    CALLS_ENDED.labels(status=status, reason=(reason or "unspecified")[:80]).inc()
    duration = max(0, duration_seconds or 0)
    CALL_DURATION.observe(duration)
    CALL_COST.observe(max(0.0, cost_cents))
    CALL_MINUTES.inc(duration / 60)
    if handoff_requested:
        observe_handoff(reason or "unspecified", completed=handoff_completed)
    for stage, values in latency_ms.items():
        if not isinstance(values, dict):
            continue
        for field, histogram in (("p50", STAGE_P50), ("p95", STAGE_P95)):
            value = values.get(field)
            if isinstance(value, (int, float)) and value >= 0:
                histogram.labels(stage=str(stage)[:40]).observe(float(value))
