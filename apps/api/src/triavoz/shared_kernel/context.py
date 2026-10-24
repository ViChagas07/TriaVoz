from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
clinic_id_var: ContextVar[str | None] = ContextVar("clinic_id", default=None)
call_id_var: ContextVar[str | None] = ContextVar("call_id", default=None)

# Mutable request-scoped bag. The HTTP middleware creates it before Starlette forks the request
# task; dependencies mutate the SAME dict, so the middleware can read the resolved tenant/call
# identifiers after `call_next` even though ContextVar writes inside the child task do not
# propagate back to the parent.
_log_ids_var: ContextVar[dict[str, str | None] | None] = ContextVar("log_ids", default=None)


def current_request_id() -> str:
    return request_id_var.get() or "-"


def current_clinic_id() -> str | None:
    ids = _log_ids_var.get()
    return (ids or {}).get("clinic_id") or clinic_id_var.get()


def current_call_id() -> str | None:
    ids = _log_ids_var.get()
    return (ids or {}).get("call_id") or call_id_var.get()


def start_log_scope() -> tuple[dict[str, str | None], Token[dict[str, str | None] | None]]:
    state: dict[str, str | None] = {"clinic_id": None, "call_id": None}
    return state, _log_ids_var.set(state)


def end_log_scope(token: Token[dict[str, str | None] | None]) -> None:
    _log_ids_var.reset(token)


def _safe(value: object, *, limit: int = 64) -> str | None:
    if value is None:
        return None
    text = re.sub(r"[^A-Za-z0-9._:-]", "", str(value))[:limit]
    return text or None


def bind_log_ids(*, clinic_id: object | None = None, call_id: object | None = None) -> None:
    """Bind identifiers for the current request (or job); middleware clears the scope."""
    clinic = _safe(clinic_id)
    call = _safe(call_id)
    ids = _log_ids_var.get()
    if ids is not None:
        if clinic is not None:
            ids["clinic_id"] = clinic
        if call is not None:
            ids["call_id"] = call
        return
    if clinic is not None:
        clinic_id_var.set(clinic)
    if call is not None:
        call_id_var.set(call)


def clear_log_ids() -> None:
    ids = _log_ids_var.get()
    if ids is not None:
        ids["clinic_id"] = None
        ids["call_id"] = None
    clinic_id_var.set(None)
    call_id_var.set(None)


@contextmanager
def log_context(
    *, clinic_id: object | None = None, call_id: object | None = None
) -> Iterator[None]:
    """Bind tenant/call identifiers to the current task's log context only.

    Values are short identifiers, never names, phone numbers or transcript content.
    """
    clinic_token: Token[str | None] | None = None
    call_token: Token[str | None] | None = None
    if clinic_id is not None:
        clinic_token = clinic_id_var.set(_safe(clinic_id))
    if call_id is not None:
        call_token = call_id_var.set(_safe(call_id))
    try:
        yield
    finally:
        if call_token is not None:
            call_id_var.reset(call_token)
        if clinic_token is not None:
            clinic_id_var.reset(clinic_token)
