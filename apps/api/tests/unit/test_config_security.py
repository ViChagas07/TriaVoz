"""Production configuration guards and credential/cookie invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from triavoz.config import Settings, get_settings
from triavoz.infrastructure.security.passwords import hash_password
from triavoz.interfaces.http.deps import client_ip


def _production(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "environment": "production",
        "jwt_secret": "j" * 48,
        "internal_hmac_secret": "h" * 48,
        "cookie_secure": True,
        "cors_origins": ["https://app.example.test"],
        "database_url_app": "postgresql+asyncpg://triavoz_app:strong@db:5432/triavoz",
        "livekit_api_key": "lk-live-key",
        "livekit_api_secret": "lk-live-secret",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


def test_production_accepts_strong_settings_and_prefixes_host_cookies() -> None:
    settings = _production()
    assert settings.cookie_host_prefix is True
    assert settings.access_cookie == "__Host-triavoz_access"
    assert settings.refresh_cookie == "__Host-triavoz_refresh"
    assert settings.caller_cookie == "__Host-triavoz_caller"


@pytest.mark.parametrize(
    "override",
    [
        {"jwt_secret": "short"},
        {"jwt_secret": "change-me-dev-only"},
        {"internal_hmac_secret": "change-me-dev-only"},
        {"cookie_secure": False},
        {"cookie_samesite": "none"},
        {"cors_origins": ["*"]},
        {"cors_origins": ["http://app.example.test"]},
        {"database_url_app": "postgresql+asyncpg://triavoz_owner:pw@db/triavoz"},
        {"livekit_api_key": "devkey"},
        {"livekit_api_secret": "secret"},
    ],
)
def test_production_rejects_weak_or_dev_defaults(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _production(**override)


def test_argon2_uses_explicit_strong_parameters() -> None:
    digest = hash_password("correct horse battery staple")
    assert digest.startswith("$argon2id$v=19$")
    assert "m=65536,t=3,p=4" in digest


def _request(peer: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw,
            "client": (peer, 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )


def test_forwarded_for_is_ignored_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "trust_forwarded_for", False)
    request = _request("10.0.0.5", {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"})
    assert client_ip(request) == "10.0.0.5"


def test_forwarded_for_is_used_only_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "trust_forwarded_for", True)
    request = _request("10.0.0.5", {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"})
    assert client_ip(request) == "203.0.113.7"
    bogus = _request("10.0.0.5", {"X-Forwarded-For": "not-an-ip"})
    assert client_ip(bogus) == "10.0.0.5"
