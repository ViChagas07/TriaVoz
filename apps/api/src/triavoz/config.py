"""Application settings. Secrets come ONLY from the environment (never hardcoded)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRIAVOZ_", env_file=".env", extra="ignore")

    environment: str = "development"

    # Runtime connection: role triavoz_app (NOBYPASSRLS, not the table owner).
    # Never the owner or a superuser.
    database_url_app: str = Field(
        default="postgresql+asyncpg://triavoz_app:change-me@localhost:5432/triavoz"
    )
    redis_url: str = "redis://localhost:6379/0"

    # Auth for the staff dashboard (JWT) — access tokens are short-lived.
    jwt_secret: SecretStr = SecretStr("change-me-dev-only")
    jwt_access_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30
    access_cookie_name: str = "triavoz_access"
    refresh_cookie_name: str = "triavoz_refresh"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Service-to-service auth between the voice worker and this API (HMAC-SHA256).
    internal_hmac_secret: SecretStr = SecretStr("change-me-dev-only")
    internal_hmac_tolerance_seconds: int = 60

    cors_origins: list[str] = ["http://localhost:3000"]

    # Voice session (server-side room creation + participant token).
    demo_clinic_slug: str = "clinica-horizonte"
    livekit_http_url: str = "http://localhost:7880"
    livekit_public_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: SecretStr = SecretStr("secret")
    livekit_token_ttl_seconds: int = 600
    # Public web demo: per-IP bucket (kept under the historical name for compatibility).
    voice_rate_capacity: int = 10
    voice_rate_refill_per_second: float = 10 / 3600
    # Per-caller bucket (same E.164) and clinic-wide bucket (all callers/IPs).
    voice_caller_capacity: int = 3
    voice_caller_refill_per_second: float = 3 / 3600
    voice_global_capacity: int = 60
    voice_global_refill_per_second: float = 60 / 3600

    # Anti-abuse / demo hardening.
    demo_hard_max_call_seconds: int = 300
    demo_daily_minute_budget: int = 120
    demo_daily_cost_budget_cents: int = 500
    demo_max_turns: int = 20
    demo_silence_timeout_seconds: float = 15.0
    abuse_review_threshold: int = 50
    cost_breaker_cooldown_seconds: int = 300
    cost_breaker_failure_threshold: int = 1

    # Spike alerts (log by default; e-mail when the SMTP settings are present).
    alert_calls_per_hour: int = 100
    alert_cost_cents_per_hour: int = 2000
    alert_prank_flags_per_hour: int = 5
    alerts_email: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True

    # Optional Cloudflare Turnstile challenge for the public demo (disabled when unset).
    turnstile_secret: SecretStr | None = None
    turnstile_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    # SSE heartbeat (seconds); the stream is served by Redis pub/sub when available.
    sse_heartbeat_seconds: int = 15
    login_account_capacity: int = 5
    login_ip_capacity: int = 30

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.is_production:
            if self.jwt_secret.get_secret_value().startswith("change-me"):
                raise ValueError("TRIAVOZ_JWT_SECRET must be set in production")
            if self.internal_hmac_secret.get_secret_value().startswith("change-me"):
                raise ValueError("TRIAVOZ_INTERNAL_HMAC_SECRET must be set in production")
            if not self.cookie_secure:
                raise ValueError("TRIAVOZ_COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
