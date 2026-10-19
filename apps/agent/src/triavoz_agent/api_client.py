"""Signed HTTP client for the TriaVoz internal API. The worker holds NO database credentials."""

from __future__ import annotations

import contextlib
import json
import time
from typing import Any

import httpx

TIMESTAMP_HEADER = "X-Triavoz-Timestamp"
SIGNATURE_HEADER = "X-Triavoz-Signature"


class ApiError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"{status}: {code}")
        self.status = status
        self.code = code


def sign(secret: str, timestamp: int, body: bytes) -> str:
    import hashlib
    import hmac

    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


class TriaVozApi:
    def __init__(
        self, base_url: str, hmac_secret: str, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._secret = hmac_secret
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=8.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        raw = json.dumps(body, default=str).encode()
        ts = int(time.time())
        headers = {
            "Content-Type": "application/json",
            TIMESTAMP_HEADER: str(ts),
            SIGNATURE_HEADER: sign(self._secret, ts, raw),
        }
        resp = await self._client.post(f"/internal/agent{path}", content=raw, headers=headers)
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

    async def tool(self, name: str, clinic_id: str, call_id: str, **kwargs: Any) -> Any:
        return await self._post(
            f"/tools/{name}", {"clinic_id": clinic_id, "call_id": call_id, **kwargs}
        )

    async def add_turns(self, clinic_id: str, call_id: str, turns: list[dict[str, Any]]) -> None:
        await self._post(
            "/calls/turns", {"clinic_id": clinic_id, "call_id": call_id, "turns": turns}
        )

    async def end_call(self, clinic_id: str, call_id: str, **fields: Any) -> None:
        await self._post("/calls/end", {"clinic_id": clinic_id, "call_id": call_id, **fields})
