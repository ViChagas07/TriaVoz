"""Single-use HMAC nonce guard (replay protection), shared through Redis when available."""

from __future__ import annotations

import asyncio
import time
from functools import lru_cache
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.config import get_settings


class ReplayGuard(Protocol):
    async def claim(self, key: str, ttl_seconds: int) -> bool: ...


class InMemoryReplayGuard:
    def __init__(self) -> None:
        self._seen: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def claim(self, key: str, ttl_seconds: int) -> bool:
        async with self._lock:
            now = time.monotonic()
            for item, expiry in list(self._seen.items()):
                if expiry <= now:
                    del self._seen[item]
            if key in self._seen:
                return False
            self._seen[key] = now + ttl_seconds
            return True


class RedisReplayGuard:
    def __init__(self, url: str) -> None:
        self._redis = Redis.from_url(
            url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
        )
        self._fallback = InMemoryReplayGuard()

    async def claim(self, key: str, ttl_seconds: int) -> bool:
        try:
            result = await self._redis.set(key, "1", nx=True, ex=max(1, ttl_seconds))
            return bool(result)
        except (RedisError, OSError):
            return await self._fallback.claim(key, ttl_seconds)


@lru_cache
def get_replay_guard() -> RedisReplayGuard:
    return RedisReplayGuard(get_settings().redis_url)
