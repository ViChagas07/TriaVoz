"""Tenant-prefixed Redis pub/sub for SSE. Publishing is best-effort; never fails a write."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from triavoz.config import get_settings

log = logging.getLogger("triavoz.events")
CHANNEL = "triavoz:clinic:{clinic_id}:events"


def _channel(clinic_id: UUID) -> str:
    return CHANNEL.format(clinic_id=clinic_id)


class RedisEventBus:
    def __init__(self, url: str) -> None:
        self._url = url
        self._redis: Redis | None = None

    def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._url, decode_responses=True, socket_connect_timeout=1, socket_timeout=2
            )
        return self._redis

    async def publish(self, clinic_id: UUID, event_type: str, data: dict[str, Any]) -> None:
        payload = json.dumps(
            {"type": event_type, "at": datetime.now(UTC).isoformat(), "data": data},
            default=str,
            ensure_ascii=False,
        )
        try:
            await self._client().publish(_channel(clinic_id), payload)
        except (RedisError, OSError) as exc:
            log.warning("event publish skipped (redis unavailable): %s", exc)

    async def subscribe(self, clinic_id: UUID) -> AsyncIterator[str]:
        """Yields SSE frames. Heartbeats keep proxies and browsers from timing out."""
        heartbeat = max(5, get_settings().sse_heartbeat_seconds)
        try:
            pubsub = self._client().pubsub()
            await pubsub.subscribe(_channel(clinic_id))
        except (RedisError, OSError) as exc:
            log.warning("event stream degraded to heartbeats: %s", exc)
            while True:
                yield ": heartbeat\n\n"
                await asyncio.sleep(heartbeat)

        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

        async def reader() -> None:
            try:
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=heartbeat
                    )
                    if message and message.get("type") == "message":
                        try:
                            queue.put_nowait(str(message["data"]))
                        except asyncio.QueueFull:
                            # Backpressure: drop the oldest event rather than growing unbounded.
                            with contextlib.suppress(asyncio.QueueEmpty):
                                queue.get_nowait()
                            queue.put_nowait(str(message["data"]))
            except (RedisError, OSError, asyncio.CancelledError):
                return

        task = asyncio.create_task(reader())
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=heartbeat)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                else:
                    yield f"event: update\ndata: {payload}\n\n"
        finally:
            task.cancel()
            try:
                await pubsub.unsubscribe(_channel(clinic_id))
                await pubsub.aclose()  # type: ignore[no-untyped-call]
            except (RedisError, OSError):
                pass


class NullEventBus:
    async def publish(self, clinic_id: UUID, event_type: str, data: dict[str, Any]) -> None:
        return None

    async def subscribe(self, clinic_id: UUID) -> AsyncIterator[str]:
        while True:
            yield ": heartbeat\n\n"
            await asyncio.sleep(max(5, get_settings().sse_heartbeat_seconds))


@lru_cache
def get_event_bus() -> RedisEventBus:
    return RedisEventBus(get_settings().redis_url)
