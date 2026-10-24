from __future__ import annotations

import json
import logging

from triavoz.config import get_settings
from triavoz.observability.logging import ContextFilter, JsonFormatter
from triavoz.observability.metrics import (
    metrics_payload,
    observe_call_ended,
    observe_http,
    observe_tool_error,
)
from triavoz.observability.sentry import init_sentry
from triavoz.observability.tracing import setup_tracing
from triavoz.shared_kernel.context import log_context


def _formatted(record: logging.LogRecord) -> dict[str, object]:
    ContextFilter().filter(record)
    formatter = JsonFormatter(service="test", environment="test")
    return json.loads(formatter.format(record))


def test_json_log_has_correlation_ids_and_no_untrusted_extra() -> None:
    with log_context(clinic_id="clinic-1", call_id="call-1"):
        record = logging.LogRecord(
            "triavoz.test",
            logging.INFO,
            __file__,
            1,
            "request_completed",
            (),
            None,
        )
        record.request_id = "req-1"
        record.customer_name = "Maria"
        payload = _formatted(record)
    assert payload["request_id"] == "req-1"
    assert payload["clinic_id"] == "clinic-1"
    assert payload["call_id"] == "call-1"
    assert payload["service"] == "test"
    assert "customer_name" not in payload
    assert "Maria" not in json.dumps(payload)


def test_json_log_records_exception_type_without_payload() -> None:
    try:
        raise RuntimeError("provider unavailable")
    except RuntimeError:
        import sys

        record = logging.LogRecord(
            "triavoz.test",
            logging.ERROR,
            __file__,
            1,
            "provider_failed",
            (),
            sys.exc_info(),
        )
        payload = _formatted(record)
    assert payload["exception"]["type"] == "RuntimeError"


def test_prometheus_exposition_contains_business_metrics() -> None:
    observe_http(method="GET", path="/health", status=200, seconds=0.01)
    observe_tool_error("book_appointment", "slot_taken")
    observe_call_ended(
        status="completed",
        reason="booking_completed",
        duration_seconds=42,
        cost_cents=2.5,
        handoff_requested=False,
        latency_ms={"llm_ttft": {"p50": 700, "p95": 900}},
    )
    text = metrics_payload().decode()
    for metric in (
        "triavoz_http_requests_total",
        "triavoz_tool_errors_total",
        "triavoz_slot_taken_total",
        "triavoz_calls_ended_total",
        "triavoz_call_duration_seconds",
        "triavoz_stage_p50_ms",
    ):
        assert metric in text


def test_sentry_and_tracing_are_noops_without_configuration() -> None:
    settings = get_settings()
    assert init_sentry(settings, service="test") is False
    assert setup_tracing(None, service_name="test-service", endpoint=None) is False
