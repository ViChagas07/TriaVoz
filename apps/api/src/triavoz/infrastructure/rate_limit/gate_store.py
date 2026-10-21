"""Shared gate state (token buckets, concurrency slots, breaker/counter JSON).

Redis is the cross-node authority; if it is unreachable the adapter falls back to process-local
state so the API keeps serving. The fallback is weaker across replicas (documented risk) but the
database budgets and the provider circuit breakers still hold.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from functools import lru_cache
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.config import get_settings
from triavoz.infrastructure.rate_limit.redis_token_bucket import RedisTokenBucket
from triavoz.shared_kernel.rate_limit import TokenBucket

_CONCURRENT_LUA = """
local key = KEYS[1]
local member = ARGV[1]
local limit = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', key, '-inf', now)
if redis.call('ZSCORE', key, member) then
  return 1
end
if redis.call('ZCARD', key) >= limit then
  return 0
end
redis.call('ZADD', key, now + ttl, member)
redis.call('EXPIRE', key, ttl + 60)
return 1
"""

_INCREMENT_LUA = """
local value = redis.call('INCRBY', KEYS[1], ARGV[2])
if value == tonumber(ARGV[2]) then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return value
"""


def concurrent_key(clinic_id: UUID) -> str:
    return f"clinic:{clinic_id}:rl:concurrent"


class InMemoryGateStore:
    """Deterministic fallback used by unit tests and when Redis is down."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._slots: dict[UUID, dict[str, float]] = {}
        self._json: dict[str, tuple[float, dict[str, Any]]] = {}
        self._strings: dict[str, tuple[float, str]] = {}
        self._counters: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool:
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(capacity, refill_per_second)
                self._buckets[key] = bucket
            bucket.capacity = capacity
            bucket.refill_per_second = refill_per_second
            return bucket.allow(time.monotonic(), cost)

    async def acquire_slot(
        self, *, clinic_id: UUID, slot_id: str, limit: int, ttl_seconds: int
    ) -> bool:
        async with self._lock:
            now = time.time()
            slots = self._slots.setdefault(clinic_id, {})
            for member, expiry in list(slots.items()):
                if expiry <= now:
                    del slots[member]
            if slot_id in slots:
                return True
            if len(slots) >= limit:
                return False
            slots[slot_id] = now + ttl_seconds
            return True

    async def release_slot(self, *, clinic_id: UUID, slot_id: str) -> None:
        async with self._lock:
            self._slots.get(clinic_id, {}).pop(slot_id, None)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        async with self._lock:
            item = self._json.get(key)
            if item is None:
                return None
            expiry, value = item
            if expiry <= time.time():
                del self._json[key]
                return None
            return dict(value)

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        async with self._lock:
            self._json[key] = (time.time() + ttl_seconds, dict(value))

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        async with self._lock:
            now = time.time()
            item = self._strings.get(key)
            if item is not None and item[0] > now:
                return False
            self._strings[key] = (now + ttl_seconds, value)
            return True

    async def increment(self, key: str, ttl_seconds: int, amount: int = 1) -> int:
        async with self._lock:
            now = time.time()
            count, expiry = self._counters.get(key, (0, now + ttl_seconds))
            if expiry <= now:
                count, expiry = 0, now + ttl_seconds
            count += amount
            self._counters[key] = (count, expiry)
            return count

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._json.pop(key, None)
            self._strings.pop(key, None)


class RedisGateStore:
    def __init__(self, url: str) -> None:
        self._redis = Redis.from_url(
            url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
        )
        self._bucket = RedisTokenBucket(self._redis)
        self._slot_script = self._redis.register_script(_CONCURRENT_LUA)
        self._increment_script = self._redis.register_script(_INCREMENT_LUA)
        self._fallback = InMemoryGateStore()

    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool:
        try:
            return await self._bucket.allow(key, capacity, refill_per_second, cost)
        except (RedisError, OSError):
            return await self._fallback.allow(key, capacity, refill_per_second, cost)

    async def acquire_slot(
        self, *, clinic_id: UUID, slot_id: str, limit: int, ttl_seconds: int
    ) -> bool:
        try:
            result = await self._slot_script(
                keys=[concurrent_key(clinic_id)],
                args=[slot_id, limit, ttl_seconds],
            )
            return bool(result)
        except (RedisError, OSError):
            return await self._fallback.acquire_slot(
                clinic_id=clinic_id, slot_id=slot_id, limit=limit, ttl_seconds=ttl_seconds
            )

    async def release_slot(self, *, clinic_id: UUID, slot_id: str) -> None:
        try:
            await self._redis.zrem(concurrent_key(clinic_id), slot_id)
        except (RedisError, OSError):
            await self._fallback.release_slot(clinic_id=clinic_id, slot_id=slot_id)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(key)
        except (RedisError, OSError):
            return await self._fallback.get_json(key)
        if not raw:
            return None
        try:
            value = json.loads(raw)
        except ValueError:
            return None
        return value if isinstance(value, dict) else None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl_seconds)
        except (RedisError, OSError):
            await self._fallback.set_json(key, value, ttl_seconds)

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        try:
            result = await self._redis.set(key, value, nx=True, ex=ttl_seconds)
            return bool(result)
        except (RedisError, OSError):
            return await self._fallback.set_if_absent(key, value, ttl_seconds)

    async def increment(self, key: str, ttl_seconds: int, amount: int = 1) -> int:
        try:
            result = await self._increment_script(keys=[key], args=[ttl_seconds, amount])
            return int(result)
        except (RedisError, OSError):
            return await self._fallback.increment(key, ttl_seconds, amount)

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except (RedisError, OSError):
            await self._fallback.delete(key)

    async def close(self) -> None:
        with contextlib.suppress(RedisError, OSError):
            await self._redis.aclose()


@lru_cache
def get_gate_store() -> RedisGateStore:
    return RedisGateStore(get_settings().redis_url)
