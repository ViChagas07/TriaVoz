"""Signed HTTP client for the TriaVoz internal API. The worker holds NO database credentials."""

from __future__ import annotations

import contextlib
import json
import secrets
import time
from typing import Any

import httpx

from triavoz_agent.resilience import Bulkhead, CircuitBreaker

TIMESTAMP_HEADER = "X-Triavoz-Timestamp"
NONCE_HEADER = "X-Triavoz-Nonce"
SIGNATURE_HEADER = "X-Triavoz-Signature"


class ApiError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"{status}: {code}")
        self.status = status
        self.code = code


def sign(secret: str, timestamp: int, body: bytes, nonce: str = "") -> str:
    import hashlib
    import hmac

    return hmac.new(
        secret.encode(), f"{timestamp}.{nonce}.".encode() + body, hashlib.sha256
    ).hexdigest()


class TriaVozApi:
    def __init__(
        self, base_url: str, hmac_secret: str, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._secret = hmac_secret
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=8.0)
        self._breaker = CircuitBreaker("internal-api", failure_threshold=5, recovery_timeout=15)
        self._bulkhead = Bulkhead("internal-api", max_concurrency=8, wait_timeout=2.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        if not self._breaker.allow():
            raise ApiError(503, "circuit_open")
        raw = json.dumps(body, default=str).encode()
        ts = int(time.time())
        nonce = secrets.token_hex(16)
        headers = {
            "Content-Type": "application/json",
            TIMESTAMP_HEADER: str(ts),
            NONCE_HEADER: nonce,
            SIGNATURE_HEADER: sign(self._secret, ts, raw, nonce),
        }
        try:
            resp = await self._bulkhead.call(
                lambda: self._client.post(f"/internal/agent{path}", content=raw, headers=headers),
                deadline=8.0,
            )
        except (httpx.HTTPError, TimeoutError) as exc:
            self._breaker.record_failure()
            raise ApiError(503, "api_unavailable") from exc
        if resp.status_code >= 500:
            self._breaker.record_failure()
        else:
            self._breaker.record_success()
        if resp.status_code >= 400:
            code = "error"
            with contextlib.suppress(ValueError):
                code = str(resp.json().get("detail", code))
            raise ApiError(resp.status_code, code)
        return resp.json()

    async def start_call(
        self, clinic_id: str, channel: str, room_name: str | None, caller_number: str | None
    ) -> str:
        data = await self._post(
            "/calls/start",
            {
                "clinic_id": clinic_id,
                "channel": channel,
                "room_name": room_name,
                "caller_number": caller_number,
            },
        )
        return str(data["call_id"])

    async def tool(
        self, name: str, clinic_id: str, call_id: str, /, **kwargs: Any
    ) -> Any:
        # Server-provided identifiers are never part of the LLM-visible tool schema. Reject an
        # accidental/overridden value instead of silently merging it into the signed payload.
        if "clinic_id" in kwargs or "call_id" in kwargs:
            raise ApiError(422, "reserved_tool_argument")
        return await self._post(
            f"/tools/{name}", {"clinic_id": clinic_id, "call_id": call_id, **kwargs}
        )

    async def add_turns(self, clinic_id: str, call_id: str, turns: list[dict[str, Any]]) -> None:
        await self._post(
            "/calls/turns", {"clinic_id": clinic_id, "call_id": call_id, "turns": turns}
        )

    async def end_call(self, clinic_id: str, call_id: str, **fields: Any) -> None:
        await self._post("/calls/end", {"clinic_id": clinic_id, "call_id": call_id, **fields})
