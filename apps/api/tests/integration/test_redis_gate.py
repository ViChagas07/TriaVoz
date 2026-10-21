"""Real-Redis validation of the Lua adapters (token bucket, concurrency, breaker state).

Skipped only when no Redis URL is configured/reachable; CI runs a Redis service.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.application.abuse.breaker import CostCircuitBreaker, breaker_key, probe_key
from triavoz.infrastructure.rate_limit.gate_store import RedisGateStore, concurrent_key
from triavoz.infrastructure.rate_limit.redis_token_bucket import RedisTokenBucket

REDIS_URL = os.environ.get("TRIAVOZ_TEST_REDIS_URL", "redis://localhost:6379/15")

pytestmark = pytest.mark.redis


@pytest.fixture
async def redis() -> Redis:
    client = Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
    try:
        await client.ping()
    except (RedisError, OSError) as exc:
        pytest.skip(f"redis unavailable at {REDIS_URL}: {exc}")
    yield client
    await client.aclose()


async def test_bucket_burst_refill_and_expiry(redis: Redis) -> None:
    bucket = RedisTokenBucket(redis)
    key = f"triavoz:test:{uuid.uuid4().hex}:bucket"

    assert await bucket.allow(key, capacity=2, refill_per_second=1.0) is True
    assert await bucket.allow(key, capacity=2, refill_per_second=1.0) is True
    assert await bucket.allow(key, capacity=2, refill_per_second=1.0) is False
    assert await redis.ttl(key) > 0, "the Lua script must set a TTL"

    await asyncio.sleep(1.05)
    assert await bucket.allow(key, capacity=2, refill_per_second=1.0) is True

    # Expiry resets the bucket to full (the script always refreshes the TTL).
    await redis.expire(key, 1)
    await asyncio.sleep(1.1)
    assert await redis.exists(key) == 0
    assert await bucket.allow(key, capacity=2, refill_per_second=1.0) is True
    await redis.delete(key)


async def test_concurrency_slots_are_atomic_and_reusable(redis: Redis) -> None:
    store = RedisGateStore(REDIS_URL)
    clinic = uuid.uuid4()
    try:
        assert (
            await store.acquire_slot(clinic_id=clinic, slot_id="a", limit=2, ttl_seconds=60) is True
        )
        assert (
            await store.acquire_slot(clinic_id=clinic, slot_id="b", limit=2, ttl_seconds=60) is True
        )
        assert (
            await store.acquire_slot(clinic_id=clinic, slot_id="c", limit=2, ttl_seconds=60)
            is False
        )
        assert await redis.zcard(concurrent_key(clinic)) == 2

        await store.release_slot(clinic_id=clinic, slot_id="a")
        assert (
            await store.acquire_slot(clinic_id=clinic, slot_id="c", limit=2, ttl_seconds=60) is True
        )
    finally:
        await redis.delete(concurrent_key(clinic))
        await store.close()


async def test_cost_breaker_state_is_shared_and_half_open(redis: Redis) -> None:
    store = RedisGateStore(REDIS_URL)
    clinic = uuid.uuid4()
    try:
        first = CostCircuitBreaker(store, clinic_id=clinic, cooldown_seconds=30)
        second = CostCircuitBreaker(store, clinic_id=clinic, cooldown_seconds=30)
        await first.trip("cost_budget", now=1000.0)
        assert (await second.snapshot()).status == "open"

        denied = await second.check(now=1010.0)
        assert denied.allowed is False and denied.retry_after_seconds > 0

        probe = await second.check(now=1031.0)
        assert probe.allowed is True and probe.half_open is True
        # A second probe while the first is in flight is refused.
        assert (await first.check(now=1031.0)).allowed is False

        await first.record_success()
        assert (await second.snapshot()).status == "closed"
    finally:
        await redis.delete(breaker_key(clinic))
        await redis.delete(probe_key(clinic))
        await store.close()
