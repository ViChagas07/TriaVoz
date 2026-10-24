"""Worker observability: one-line JSON logs, optional Sentry and OTel traces.

No transcript text, caller number, patient name or tool payload is ever logged. The only
identifiers are `clinic_id`, `call_id` and the OTel `trace_id`/`span_id`.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from triavoz_agent.config import WorkerConfig

clinic_id_var: ContextVar[str | None] = ContextVar("clinic_id", default=None)
call_id_var: ContextVar[str | None] = ContextVar("call_id", default=None)

_CONFIGURED = False
_TRACING_CONFIGURED = False
_SENTRY_CONFIGURED = False

_ALLOWED_EXTRA = {
    "channel",
    "code",
    "duration_ms",
    "end_reason",
    "event",
    "reason",
    "stage",
    "status",
    "tool",
}


def bind_call_context(*, clinic_id: object | None = None, call_id: object | None = None) -> None:
    if clinic_id is not None:
        clinic_id_var.set(str(clinic_id)[:64])
    if call_id is not None:
        call_id_var.set(str(call_id)[:64])


def _trace_fields() -> tuple[str | None, str | None]:
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if not ctx.is_valid:
            return None, None
        return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:  # pragma: no cover - tracing is optional
        return None, None


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.clinic_id = getattr(record, "clinic_id", None) or clinic_id_var.get()
        record.call_id = getattr(record, "call_id", None) or call_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service: str, environment: str) -> None:
        super().__init__()
        self.service = service
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "service": self.service,
            "environment": self.environment,
            "message": record.getMessage(),
        }
        for field in ("clinic_id", "call_id"):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        trace_id, span_id = _trace_fields()
        if trace_id:
            payload["trace_id"] = trace_id
            payload["span_id"] = span_id
        for key, value in record.__dict__.items():
            if key in _ALLOWED_EXTRA and value is not None:
                payload[key] = value
        if record.exc_info:
            exc_type, exc, _ = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else "Exception",
                "message": str(exc) if exc else "",
            }
        return json.dumps(payload, ensure_ascii=False, default=str)


class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        ids = " ".join(
            f"{name}={value}"
            for name in ("clinic_id", "call_id")
            if (value := getattr(record, name, None))
        )
        return f"{base} {ids}".rstrip()


def configure_logging(cfg: WorkerConfig) -> None:
    global _CONFIGURED
    if _CONFIGURED or "pytest" in sys.modules:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if cfg.log_format == "plain":
        handler.setFormatter(PlainFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(JsonFormatter(service=cfg.otel_service_name, environment="worker"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    _CONFIGURED = True


def _scrub_event(event: Any, _hint: Any) -> Any:
    event.pop("request", None)
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    return event


def init_sentry(cfg: WorkerConfig) -> bool:
    global _SENTRY_CONFIGURED
    if not cfg.sentry_dsn or _SENTRY_CONFIGURED:
        return _SENTRY_CONFIGURED
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - dependency is pinned
        return False
    sentry_sdk.init(
        dsn=cfg.sentry_dsn,
        environment="worker",
        release=cfg.sentry_release or cfg.otel_service_name,
        traces_sample_rate=max(0.0, min(1.0, cfg.sentry_traces_sample_rate)),
        send_default_pii=False,
        max_request_body_size="never",
        max_breadcrumbs=0,
        before_send=_scrub_event,
    )
    _SENTRY_CONFIGURED = True
    return True


def capture_exception(exc: BaseException) -> None:
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:  # pragma: no cover - optional
        return


def setup_tracing(cfg: WorkerConfig) -> bool:
    global _TRACING_CONFIGURED
    if not cfg.otel_exporter_endpoint or _TRACING_CONFIGURED:
        return _TRACING_CONFIGURED
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError:  # pragma: no cover - optional extra
        return False

    url = cfg.otel_exporter_endpoint.rstrip("/")
    if not url.endswith("/v1/traces"):
        url = f"{url}/v1/traces"
    provider = TracerProvider(
        resource=Resource.create({"service.name": cfg.otel_service_name}),
        sampler=ParentBased(TraceIdRatioBased(max(0.0, min(1.0, cfg.otel_sample_ratio)))),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=url)))
    trace.set_tracer_provider(provider)
    # Propagates W3C traceparent on the worker -> API HMAC calls; the API joins the same trace.
    HTTPXClientInstrumentor().instrument()
    _TRACING_CONFIGURED = True
    return True
