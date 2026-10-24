"""Optional Sentry error tracking. Disabled unless TRIAVOZ_SENTRY_DSN is set."""

from __future__ import annotations

import logging
from typing import Any

from triavoz.config import Settings

log = logging.getLogger("triavoz.sentry")
_SENTRY_CONFIGURED = False


def _scrub_event(event: Any, _hint: Any) -> Any:
    # Requests may carry cookies/authorization; transcripts are never attached, but drop the whole
    # request payload to keep PII out of the error tracker.
    event.pop("request", None)
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    return event


def init_sentry(settings: Settings, *, service: str) -> bool:
    global _SENTRY_CONFIGURED
    if settings.sentry_dsn is None or _SENTRY_CONFIGURED:
        return _SENTRY_CONFIGURED
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:  # pragma: no cover - dependency is pinned
        log.warning("sentry_sdk is not installed; error tracking stays disabled")
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.environment,
        release=settings.sentry_release or service,
        traces_sample_rate=max(0.0, min(1.0, settings.sentry_traces_sample_rate)),
        send_default_pii=False,
        max_request_body_size="never",
        max_breadcrumbs=0,
        before_send=_scrub_event,
        integrations=[StarletteIntegration(), FastApiIntegration()],
    )
    _SENTRY_CONFIGURED = True
    return True
