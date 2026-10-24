"""Optional Turnstile challenge: disabled is a no-op, failures fail closed."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from triavoz.config import Settings
from triavoz.infrastructure.security.turnstile import TurnstileVerifier


class _Response:
    def __init__(self, success: bool) -> None:
        self._success = success

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, bool]:
        return {"success": self._success}


class _Client:
    instances: list[_Client] = []

    def __init__(self, *, result: bool | Exception) -> None:
        self.result = result
        self.posts: list[tuple[str, dict[str, Any]]] = []
        _Client.instances.append(self)

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, data: dict[str, Any]) -> _Response:
        self.posts.append((url, data))
        if isinstance(self.result, Exception):
            raise self.result
        return _Response(self.result)


def _settings(**kwargs: Any) -> Settings:
    return Settings(_env_file=None, **kwargs)


async def test_turnstile_is_disabled_without_a_secret() -> None:
    verifier = TurnstileVerifier(_settings())
    assert verifier.enabled is False
    assert await verifier.verify(None, "203.0.113.1") is True
    assert await verifier.verify("token", "203.0.113.1") is True


async def test_turnstile_posts_the_secret_and_rejects_a_missing_or_failed_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _Client.instances.clear()
    monkeypatch.setattr(
        "triavoz.infrastructure.security.turnstile.httpx.AsyncClient",
        lambda **_: _Client(result=True),
    )
    verifier = TurnstileVerifier(_settings(turnstile_secret="turnstile-secret"))
    assert verifier.enabled is True
    assert await verifier.verify(None, "203.0.113.2") is False
    assert await verifier.verify("challenge-token", "203.0.113.2") is True
    url, payload = _Client.instances[0].posts[0]
    assert url == verifier._url
    assert payload == {
        "secret": "turnstile-secret",
        "response": "challenge-token",
        "remoteip": "203.0.113.2",
    }

    _Client.instances.clear()
    monkeypatch.setattr(
        "triavoz.infrastructure.security.turnstile.httpx.AsyncClient",
        lambda **_: _Client(result=False),
    )
    assert (
        await TurnstileVerifier(_settings(turnstile_secret="turnstile-secret")).verify(
            "challenge-token", "203.0.113.2"
        )
        is False
    )


async def test_turnstile_fails_closed_and_opens_the_breaker_when_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _Client.instances.clear()
    monkeypatch.setattr(
        "triavoz.infrastructure.security.turnstile.httpx.AsyncClient",
        lambda **_: _Client(result=httpx.ConnectError("down")),
    )
    verifier = TurnstileVerifier(_settings(turnstile_secret="turnstile-secret"))
    for _ in range(3):
        assert await verifier.verify("challenge-token", "203.0.113.3") is False
    assert len(_Client.instances) == 3
    # The breaker is open: no fourth provider call is attempted.
    assert await verifier.verify("challenge-token", "203.0.113.3") is False
    assert len(_Client.instances) == 3
