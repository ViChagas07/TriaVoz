from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from triavoz.shared_kernel.context import current_request_id
from triavoz.shared_kernel.errors import (
    AuthenticationError,
    Conflict,
    DomainError,
    Forbidden,
    InvalidRequest,
    NotFound,
    ServiceUnavailable,
    SlotTaken,
    SlotUnavailable,
    TooManyAttempts,
)

log = logging.getLogger("triavoz.http")


def _body(code: str) -> dict[str, str]:
    return {"detail": code, "request_id": current_request_id()}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = {
            AuthenticationError: 401,
            TooManyAttempts: 429,
            Forbidden: 403,
            NotFound: 404,
            SlotTaken: 409,
            SlotUnavailable: 409,
            Conflict: 409,
            InvalidRequest: 422,
            ServiceUnavailable: 503,
        }.get(type(exc), 400)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(status_code=status, content=_body(exc.code), headers=headers)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(detail),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled request error request_id=%s", current_request_id())
        return JSONResponse(status_code=500, content=_body("internal_error"))
