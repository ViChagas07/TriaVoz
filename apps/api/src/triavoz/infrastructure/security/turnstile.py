"""Optional Cloudflare Turnstile verification for the public demo.

Disabled unless TRIAVOZ_TURNSTILE_SECRET is configured. The call is bounded by a timeout and
fails closed when the challenge service is unreachable (prevents a free-for-all if Turnstile is on).
"""

from __future__ import annotations

import logging

import httpx

from triavoz.config import Settings
from triavoz.shared_kernel.resilience import (
    Bulkhead,
    CircuitBreaker,
    guarded_call,
)

log = logging.getLogger("triavoz.turnstile")


class TurnstileVerifier:
    def __init__(self, settings: Settings) -> None:
        self._secret = (
            settings.turnstile_secret.get_secret_value() if settings.turnstile_secret else None
        )
        self._url = settings.turnstile_verify_url
        self._breaker = CircuitBreaker("turnstile", failure_threshold=3, recovery_timeout=30)
        self._bulkhead = Bulkhead("turnstile", max_concurrency=10, wait_timeout=1.0)

    @property
    def enabled(self) -> bool:
        return bool(self._secret)

    async def verify(self, token: str | None, remote_ip: str) -> bool:
        if not self._secret:
            return True
        if not token:
            return False

        async def _verify() -> bool:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    self._url,
                    data={
                        "secret": self._secret,
                        "response": token,
                        "remoteip": remote_ip,
                    },
                )
                response.raise_for_status()
                body = response.json()
                return bool(body.get("success"))

        try:
            return await guarded_call(
                _verify, breaker=self._breaker, bulkhead=self._bulkhead, timeout_seconds=3.5
            )
        except Exception:
            log.warning("turnstile verification unavailable")
            return False
