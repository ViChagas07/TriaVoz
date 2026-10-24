from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response

from triavoz.config import get_settings
from triavoz.observability.metrics import observe_http
from triavoz.shared_kernel.context import (
    current_call_id,
    current_clinic_id,
    end_log_scope,
    request_id_var,
    start_log_scope,
)

log = logging.getLogger("triavoz.request")


class RequestBodyLimitMiddleware:
    """Reject oversized bodies even when Content-Length is absent (chunked uploads).

    The API only accepts small JSON documents; bounding this before parsing protects the process
    from memory/CPU exhaustion on every route (authenticated or not).
    """

    def __init__(self, app: Any, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max(1, max_bytes)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        declared = headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await _send_413(send)
                    return
            except ValueError:
                await _send_413(send)
                return
        # Buffer up to the cap, then replay the exact body downstream. This makes the 413
        # deterministic even on chunked requests, where exceptions inside `receive()` are turned
        # into a generic 400 by the request-body parser.
        chunks: list[bytes] = []
        received = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            received += len(chunk)
            if received > self.max_bytes:
                await _send_413(send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        replayed = False

        async def replay_receive() -> Any:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            # Long-lived responses (SSE) still need the real disconnect signal.
            return await receive()

        await self.app(scope, replay_receive, send)


async def _send_413(send: Any) -> None:
    body = json.dumps({"detail": "payload_too_large"}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _route_path(request: Request) -> str:
    """Low-cardinality label: the route template, never a resource UUID."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


def _annotate_span(request: Request, request_id: str) -> None:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if not span.get_span_context().is_valid:
            return
        span.set_attribute("triavoz.request_id", request_id)
        clinic_id, call_id = current_clinic_id(), current_call_id()
        if clinic_id:
            span.set_attribute("triavoz.clinic_id", clinic_id)
        if call_id:
            span.set_attribute("triavoz.call_id", call_id)
    except Exception:  # pragma: no cover - tracing is optional
        return


def _security_headers(response: Response, *, production: bool) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    if production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
        )


def register_request_middleware(app: FastAPI) -> None:
    settings = get_settings()
    metrics_enabled = settings.metrics_enabled

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID")
        # Strip controls/newlines so a caller cannot forge log lines.
        request_id = re.sub(r"[^A-Za-z0-9._:-]", "", incoming or "")[:100]
        if not request_id:
            request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)
        _scope, scope_token = start_log_scope()
        started = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - started
            if metrics_enabled:
                observe_http(
                    method=request.method,
                    path=_route_path(request),
                    status=500,
                    seconds=duration,
                )
            # The generic exception handler builds the JSON body; this log never includes content.
            log.exception(
                "request_failed method=%s path=%s request_id=%s duration_ms=%.1f",
                request.method,
                request.url.path,
                request_id,
                duration * 1000,
            )
            end_log_scope(scope_token)
            request_id_var.reset(token)
            raise
        duration = time.perf_counter() - started
        clinic_id, call_id = current_clinic_id(), current_call_id()
        _annotate_span(request, request_id)
        if metrics_enabled:
            observe_http(
                method=request.method,
                path=_route_path(request),
                status=response.status_code,
                seconds=duration,
            )
        response.headers["X-Request-ID"] = request_id
        _security_headers(response, production=settings.is_production)
        log.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": _route_path(request),
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 1),
                "request_id": request_id,
                "clinic_id": clinic_id,
                "call_id": call_id,
            },
        )
        end_log_scope(scope_token)
        request_id_var.reset(token)
        return response

    # Added last so it is the OUTERMOST middleware and rejects oversized bodies before parsing.
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.max_request_body_bytes)
