"""Small resilience primitives: Circuit Breaker, Bulkhead and timeouts (no I/O).

They protect calls to providers (LiveKit, LLM, STT, TTS). The state machine is pure so it can be
unit-tested with an injected clock; the API/worker can hold one instance per provider or share it.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when a provider call is short-circuited (no request is made)."""


class BulkheadFullError(RuntimeError):
    """Raised when the bulkhead has no free slot within the wait budget."""


class ProviderTimeoutError(TimeoutError):
    """Raised when a provider call exceeds its deadline."""


@dataclass
class CircuitBreaker:
    """closed -> open on failures -> half-open after cooldown -> closed on success.

    In ``half_open`` only one probe is allowed at a time; a failed probe reopens the circuit.
    """

    name: str
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1
    state: Literal["closed", "open", "half_open"] = "closed"
    failures: int = 0
    opened_at: float = 0.0
    _half_open_inflight: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def _now(self) -> float:
        return time.monotonic()

    def allow(self, now: float | None = None) -> bool:
        current = self._now() if now is None else now
        if self.state == "closed":
            return True
        if self.state == "open":
            if current - self.opened_at < self.recovery_timeout:
                return False
            # Cooldown elapsed: reopen as half-open and let exactly one probe through.
            self.state = "half_open"
            self._half_open_inflight = 0
        if self._half_open_inflight >= self.half_open_max_calls:
            return False
        self._half_open_inflight += 1
        return True

    def record_success(self) -> None:
        self.state = "closed"
        self.failures = 0
        self._half_open_inflight = 0

    def record_failure(self, now: float | None = None) -> None:
        current = self._now() if now is None else now
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = current
            self._half_open_inflight = 0

    async def call(
        self,
        fn: Callable[[], Awaitable[T]],
        *,
        timeout_seconds: float | None = None,
    ) -> T:
        async with self._lock:
            if not self.allow():
                raise CircuitOpenError(self.name)
        try:
            result = await with_timeout(fn(), timeout_seconds)
        except BaseException:
            self.record_failure()
            raise
        self.record_success()
        return result


@dataclass
class Bulkhead:
    """Caps concurrent in-flight provider calls and bounds the wait for a free slot."""

    name: str
    max_concurrency: int
    wait_timeout: float = 1.0
    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(max(1, self.max_concurrency))

    async def call(
        self, fn: Callable[[], Awaitable[T]], *, timeout_seconds: float | None = None
    ) -> T:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.wait_timeout)
        except TimeoutError as exc:
            raise BulkheadFullError(self.name) from exc
        try:
            return await with_timeout(fn(), timeout_seconds)
        finally:
            self._semaphore.release()


async def with_timeout(awaitable: Awaitable[T], timeout_seconds: float | None) -> T:
    if timeout_seconds is None:
        return await awaitable
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise ProviderTimeoutError(f"provider call exceeded {timeout_seconds}s") from exc


async def guarded_call(
    fn: Callable[[], Awaitable[T]],
    *,
    breaker: CircuitBreaker | None = None,
    bulkhead: Bulkhead | None = None,
    timeout_seconds: float | None = None,
) -> T:
    """Convenience composition: bulkhead -> breaker -> timeout."""
    if bulkhead is not None:
        return await bulkhead.call(
            lambda: _with_breaker(fn, breaker, timeout_seconds),
            timeout_seconds=timeout_seconds,
        )
    return await _with_breaker(fn, breaker, timeout_seconds)


async def _with_breaker(
    fn: Callable[[], Awaitable[T]],
    breaker: CircuitBreaker | None,
    timeout_seconds: float | None,
) -> T:
    if breaker is not None:
        return await breaker.call(fn, timeout_seconds=timeout_seconds)
    return await with_timeout(fn(), timeout_seconds)


def describe_guard(breaker: CircuitBreaker | None, bulkhead: Bulkhead | None) -> dict[str, Any]:
    """Safe diagnostics for health/logs (never includes payloads or caller data)."""
    return {
        "breaker": {
            "name": breaker.name if breaker else None,
            "state": breaker.state if breaker else None,
            "failures": breaker.failures if breaker else None,
        },
        "bulkhead": {
            "name": bulkhead.name if bulkhead else None,
            "max_concurrency": bulkhead.max_concurrency if bulkhead else None,
        },
    }
