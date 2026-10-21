from __future__ import annotations

import asyncio

import pytest

from triavoz.shared_kernel.resilience import (
    Bulkhead,
    BulkheadFullError,
    CircuitBreaker,
    CircuitOpenError,
    ProviderTimeoutError,
    describe_guard,
    guarded_call,
)


def test_breaker_closed_open_half_open_closed() -> None:
    breaker = CircuitBreaker("livekit", failure_threshold=2, recovery_timeout=30)
    assert breaker.allow(now=0) is True
    breaker.record_failure(now=0)
    assert breaker.allow(now=1) is True
    breaker.record_failure(now=1)
    assert breaker.state == "open"
    assert breaker.allow(now=10) is False
    assert breaker.allow(now=31) is True
    assert breaker.state == "half_open"
    assert breaker.allow(now=31) is False  # only one probe
    breaker.record_success()
    assert breaker.state == "closed"


async def test_breaker_call_short_circuits_and_records_success() -> None:
    breaker = CircuitBreaker("llm", failure_threshold=1, recovery_timeout=30)
    calls = 0

    async def fail() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("provider down")

    with pytest.raises(RuntimeError):
        await breaker.call(fail)
    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        await breaker.call(fail)
    assert calls == 1

    breaker.record_success()
    assert await breaker.call(lambda: _ok()) == "ok"


async def _ok() -> str:
    return "ok"


async def test_bulkhead_caps_concurrency() -> None:
    bulkhead = Bulkhead("livekit", max_concurrency=1, wait_timeout=0.05)
    release = asyncio.Event()

    async def hold() -> str:
        await release.wait()
        return "done"

    first = asyncio.create_task(bulkhead.call(hold, timeout_seconds=1))
    await asyncio.sleep(0.01)
    with pytest.raises(BulkheadFullError):
        await bulkhead.call(hold, timeout_seconds=1)
    release.set()
    assert await first == "done"


async def test_timeout_and_composed_guard() -> None:
    async def slow() -> None:
        await asyncio.sleep(0.2)

    with pytest.raises(ProviderTimeoutError):
        await guarded_call(slow, timeout_seconds=0.01)

    breaker = CircuitBreaker("x")
    bulkhead = Bulkhead("x", max_concurrency=2)
    assert await guarded_call(_ok, breaker=breaker, bulkhead=bulkhead, timeout_seconds=1) == "ok"
    assert describe_guard(breaker, bulkhead)["breaker"]["state"] == "closed"
