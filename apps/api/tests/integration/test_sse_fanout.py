"""Real-Redis SSE fan-out: a tenant's stream receives only that tenant's events."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.infrastructure.events.redis_events import CHANNEL, RedisEventBus

pytestmark = pytest.mark.redis

REDIS_URL = os.environ.get("TRIAVOZ_TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
    try:
        await client.ping()
    except (RedisError, OSError) as exc:
        pytest.skip(f"redis unavailable at {REDIS_URL}: {exc}")
    yield client
    await client.aclose()


def _channel(clinic_id: uuid.UUID) -> str:
    return CHANNEL.format(clinic_id=clinic_id)


async def _wait_subscribed(redis: Redis, channel: str, count: int = 1) -> None:
    for _ in range(100):
        result = await redis.pubsub_numsub(channel)
        if result and result[0][1] >= count:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"no subscriber on {channel}")


async def test_event_bus_fans_out_only_to_the_matching_tenant(redis: Redis) -> None:
    bus = RedisEventBus(REDIS_URL)
    clinic_a, clinic_b = uuid.uuid4(), uuid.uuid4()
    seen_a: list[dict[str, Any]] = []
    seen_b: list[dict[str, Any]] = []
    ready = asyncio.Event()

    async def collect(clinic_id: uuid.UUID, sink: list[dict[str, Any]]) -> None:
        ready.set()
        async for frame in bus.subscribe(clinic_id):
            if frame.startswith("event: update"):
                sink.append(json.loads(frame.split("data: ", 1)[1]))

    task_a = asyncio.create_task(collect(clinic_a, seen_a))
    task_b = asyncio.create_task(collect(clinic_b, seen_b))
    try:
        await asyncio.wait_for(ready.wait(), 2)
        await _wait_subscribed(redis, _channel(clinic_a))
        await _wait_subscribed(redis, _channel(clinic_b))

        await bus.publish(clinic_a, "appointment.created", {"appointment_id": "a-1"})
        await asyncio.sleep(0.4)
        await bus.publish(clinic_b, "request.created", {"request_id": "b-1"})
        await asyncio.sleep(0.4)

        assert [event["type"] for event in seen_a] == ["appointment.created"]
        assert seen_a[0]["data"] == {"appointment_id": "a-1"}
        assert [event["type"] for event in seen_b] == ["request.created"]
        assert seen_b[0]["data"] == {"request_id": "b-1"}
    finally:
        task_a.cancel()
        task_b.cancel()
        await asyncio.gather(task_a, task_b, return_exceptions=True)
