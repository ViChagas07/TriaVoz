from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response

from triavoz.shared_kernel.context import request_id_var

log = logging.getLogger("triavoz.request")


def register_request_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming[:100] if incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            # The generic exception handler builds the JSON body; this log never includes content.
            log.exception(
                "request_failed method=%s path=%s request_id=%s",
                request.method,
                request.url.path,
                request_id,
            )
            raise
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            request_id,
        )
        return response
