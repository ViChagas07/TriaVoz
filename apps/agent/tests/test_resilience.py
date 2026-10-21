import asyncio

import pytest

from triavoz_agent.resilience import Bulkhead, CircuitBreaker, ProviderTimeoutError


async def test_breaker_opens_recovers_half_open_and_closes() -> None:
    breaker = CircuitBreaker("llm", failure_threshold=2, recovery_timeout=30)
    assert breaker.allow(now=0)
    breaker.record_failure(now=0)
    assert breaker.allow(now=1)
    breaker.record_failure(now=1)
    assert breaker.state == "open"
    assert not breaker.allow(now=10)
    assert breaker.allow(now=40)  # cooldown elapsed -> one half-open probe
    assert breaker.state == "half_open"
    breaker.record_success()
    assert breaker.state == "closed"


async def test_bulkhead_caps_concurrency_and_times_out() -> None:
    bulkhead = Bulkhead("tts", max_concurrency=1, wait_timeout=0.05)
    release = asyncio.Event()

    async def hold() -> str:
        await release.wait()
        return "ok"

    first = asyncio.create_task(bulkhead.call(hold, deadline=1))
    await asyncio.sleep(0.01)
    with pytest.raises(ProviderTimeoutError):
        await bulkhead.call(hold, deadline=1)
    release.set()
    assert await first == "ok"


async def test_provider_deadline_raises_timeout() -> None:
    bulkhead = Bulkhead("stt", max_concurrency=1, wait_timeout=0.1)

    async def slow() -> None:
        await asyncio.sleep(0.2)

    with pytest.raises(ProviderTimeoutError):
        await bulkhead.call(slow, deadline=0.01)
