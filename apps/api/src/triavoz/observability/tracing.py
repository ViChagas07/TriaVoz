"""Optional OpenTelemetry tracing. Enabled by TRIAVOZ_OTEL_EXPORTER_ENDPOINT.

The API and the voice worker export OTLP/HTTP spans to the same collector; httpx instrumentation
propagates W3C `traceparent` on every HMAC-signed worker -> API call, so a call is one trace.
"""

from __future__ import annotations

import logging
from typing import Any

from triavoz.config import Settings

log = logging.getLogger("triavoz.tracing")
_CONFIGURED: set[str] = set()


def setup_tracing(
    app: Any,
    *,
    service_name: str,
    endpoint: str | None,
    sample_ratio: float = 1.0,
) -> bool:
    if not endpoint:
        return False
    if service_name in _CONFIGURED:
        return True
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError:  # pragma: no cover - optional extra
        log.warning("OpenTelemetry packages are missing; traces stay disabled")
        return False

    url = endpoint.rstrip("/")
    if not url.endswith("/v1/traces"):
        url = f"{url}/v1/traces"
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
        sampler=ParentBased(TraceIdRatioBased(max(0.0, min(1.0, sample_ratio)))),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=url)))
    trace.set_tracer_provider(provider)
    HTTPXClientInstrumentor().instrument()
    if app is not None:
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    _CONFIGURED.add(service_name)
    log.info("tracing enabled service=%s endpoint=%s", service_name, url)
    return True


def current_trace_ids() -> tuple[str | None, str | None]:
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if not ctx.is_valid:
            return None, None
        return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:  # pragma: no cover - tracing is optional
        return None, None


def setup_from_settings(app: Any, settings: Settings) -> bool:
    return setup_tracing(
        app,
        service_name=settings.otel_service_name,
        endpoint=settings.otel_exporter_endpoint,
        sample_ratio=settings.otel_sample_ratio,
    )
