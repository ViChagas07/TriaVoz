"""One-line JSON logs with request/tenant/call correlation and no payload content.

Every log record carries `request_id`, `clinic_id` and `call_id` from contextvars. Transcripts,
names, phone numbers and tool payloads are never accepted by this formatter; only allowlisted
operational fields are copied from `extra`.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from triavoz.config import Settings
from triavoz.shared_kernel.context import (
    current_call_id,
    current_clinic_id,
    request_id_var,
)

_CONFIGURED: set[str] = set()

_ALLOWED_EXTRA = {
    "channel",
    "code",
    "duration_ms",
    "end_reason",
    "event",
    "method",
    "path",
    "reason",
    "stage",
    "status",
    "tool",
    "tokens",
}


def _trace_fields() -> tuple[str | None, str | None]:
    try:
        from opentelemetry import trace

        span_context = trace.get_current_span().get_span_context()
        if not span_context.is_valid:
            return None, None
        return format(span_context.trace_id, "032x"), format(span_context.span_id, "016x")
    except Exception:  # pragma: no cover - tracing is optional
        return None, None


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", None) or request_id_var.get()
        record.clinic_id = getattr(record, "clinic_id", None) or current_clinic_id()
        record.call_id = getattr(record, "call_id", None) or current_call_id()
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
        for field in ("request_id", "clinic_id", "call_id"):
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
            for name in ("request_id", "clinic_id", "call_id")
            if (value := getattr(record, name, None))
        )
        return f"{base} {ids}".rstrip()


def configure_logging(settings: Settings, *, service: str = "triavoz-api") -> None:
    """Install the process log format once. Tests keep their own handlers."""
    if service in _CONFIGURED or "pytest" in sys.modules:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if settings.log_format == "plain":
        handler.setFormatter(PlainFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(JsonFormatter(service=service, environment=settings.environment))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # The request middleware already logs method/path/status/duration as structured JSON.
    logging.getLogger("uvicorn.access").disabled = True
    _CONFIGURED.add(service)
