"""Idempotency for mutating voice-tool endpoints.

Redis stores a small JSON response for 10 minutes; if Redis is unavailable the process-local
fallback still protects retries on the same worker. The database remains the final arbiter.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.config import get_settings

_MEMORY: dict[str, tuple[float, dict[str, Any]]] = {}
_TTL = 600


class IdempotencyStore:
    def __init__(self, url: str) -> None:
        self._redis: Redis | None = None
        self._url = url

    def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
            )
        return self._redis

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await self._client().get(f"triavoz:idem:{key}")
            return json.loads(raw) if raw else None
        except (RedisError, OSError, ValueError):
            item = _MEMORY.get(key)
            if item and item[0] > time.time():
                return item[1]
            return None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        try:
            await self._client().set(f"triavoz:idem:{key}", json.dumps(value), ex=_TTL)
        except (RedisError, OSError):
            _MEMORY[key] = (time.time() + _TTL, value)


@lru_cache
def get_idempotency_store() -> IdempotencyStore:
    return IdempotencyStore(get_settings().redis_url)
