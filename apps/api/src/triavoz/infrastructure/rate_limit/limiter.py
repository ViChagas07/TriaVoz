"""Rate limiter selection: Redis when reachable, process-local fallback otherwise.

The fallback keeps the demo and tests working without Redis; in production Redis is the shared
authority. A Redis outage must not take authentication down, but it does reduce cross-node
protection until Redis recovers (documented risk).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from functools import lru_cache

from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.redis_token_bucket import RedisTokenBucket
from triavoz.shared_kernel.rate_limit import TokenBucket

log = logging.getLogger("triavoz.rate_limit")


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool:
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(capacity, refill_per_second)
                self._buckets[key] = bucket
            return bucket.allow(asyncio.get_running_loop().time(), cost)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._buckets.pop(key, None)


class RedisRateLimiter:
    def __init__(self, url: str) -> None:
        self._redis = Redis.from_url(
            url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
        )
        self._bucket = RedisTokenBucket(self._redis)
        self._fallback = InMemoryRateLimiter()
        self._warned = False

    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool:
        try:
            return await self._bucket.allow(key, capacity, refill_per_second, cost)
        except (RedisError, OSError) as exc:
            if not self._warned:
                log.warning("redis rate limiter unavailable; using local fallback: %s", exc)
                self._warned = True
            return await self._fallback.allow(key, capacity, refill_per_second, cost)

    async def reset(self, key: str) -> None:
        await self._fallback.reset(key)
        with contextlib.suppress(RedisError, OSError):
            await self._redis.delete(key)


@lru_cache
def get_limiter() -> RedisRateLimiter:
    return RedisRateLimiter(get_settings().redis_url)
