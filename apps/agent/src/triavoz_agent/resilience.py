"""Resilience primitives for provider calls made by the voice worker.

The worker gets the same closed/open/half-open breaker and bulkhead semantics as the API. Fallbacks:
  * internal API unavailable -> tool call fails calmly; the handoff/callback path still works
  * LiveKit room connect / session start / greeting timeout -> request a callback and close
  * LLM/STT/TTS provider failure -> LiveKit Agents raises; the worker speaks a fixed fallback if TTS
    still works, records a provider_failure handoff, and ends the call.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


class ProviderTimeoutError(TimeoutError):
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    state: Literal["closed", "open", "half_open"] = "closed"
    failures: int = 0
    opened_at: float = 0.0

    def allow(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        if self.state == "closed":
            return True
        if self.state == "open" and current - self.opened_at >= self.recovery_timeout:
            self.state = "half_open"
            return True
        return self.state == "half_open"

    def record_success(self) -> None:
        self.state = "closed"
        self.failures = 0

    def record_failure(self, now: float | None = None) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = time.monotonic() if now is None else now


@dataclass
class Bulkhead:
    name: str
    max_concurrency: int
    wait_timeout: float = 1.0
    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(max(1, self.max_concurrency))

    async def call(self, fn: Callable[[], Awaitable[T]], *, deadline: float) -> T:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.wait_timeout)
        except TimeoutError as exc:
            raise ProviderTimeoutError(self.name) from exc
        try:
            return await with_timeout(fn, deadline)
        finally:
            self._semaphore.release()


async def with_timeout(fn: Callable[[], Awaitable[T]], deadline: float) -> T:
    try:
        return await asyncio.wait_for(fn(), timeout=deadline)
    except TimeoutError as exc:
        raise ProviderTimeoutError(f"{deadline}s") from exc
