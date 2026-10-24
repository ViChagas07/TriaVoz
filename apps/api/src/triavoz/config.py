"""Application settings. Secrets come ONLY from the environment (never hardcoded)."""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    # Public demo ownership cookie: an opaque browser identity, never a phone number.
    caller_cookie_name: str = "triavoz_caller"
    caller_cookie_ttl_days: int = 365
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    # __Host- requires Secure + Path=/ and forbids Domain. Enabled automatically in production.
    cookie_host_prefix: bool = False
    # Constant-time floor for the login endpoint (reduces clinic/account enumeration signals).
    login_min_seconds: float = 0.25

    # Service-to-service auth between the voice worker and this API (HMAC-SHA256).
    internal_hmac_secret: SecretStr = SecretStr("change-me-dev-only")
    # Rotation: verification accepts the previous secret while the worker is being rotated.
    internal_hmac_secret_previous: SecretStr | None = None
    internal_hmac_tolerance_seconds: int = 60
    # Optional network allow-list for /internal/* (CIDRs). Empty = rely on HMAC + proxy isolation.
    internal_allowed_cidrs: list[str] = Field(default_factory=list)
    # Only enable behind a proxy that overwrites X-Forwarded-For. Without it every client shares
    # the proxy IP and per-IP auth/voice buckets collapse into one global bucket.
    trust_forwarded_for: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]

    # DoS limits. The HTTP middleware rejects larger bodies (chunked or Content-Length).
    max_request_body_bytes: int = 1_048_576
    sse_max_connections_per_user: int = 2
    sse_max_connections_per_clinic: int = 50
    refresh_ip_capacity: int = 60
    refresh_ip_refill_per_second: float = 1.0
    internal_rate_capacity: int = 6000
    internal_rate_refill_per_second: float = 100.0
    metrics_rate_capacity: int = 120
    metrics_rate_refill_per_second: float = 2.0

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

    # Observability. Everything is opt-in except structured logs and the Prometheus endpoint.
    log_format: Literal["json", "plain"] = "json"
    metrics_enabled: bool = True
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = 0.0
    sentry_release: str | None = None
    # OTLP/HTTP collector base URL (the code appends /v1/traces when needed).
    otel_exporter_endpoint: str | None = None
    otel_service_name: str = "triavoz-api"
    otel_sample_ratio: float = 1.0

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def access_cookie(self) -> str:
        if self.cookie_host_prefix:
            return f"__Host-{self.access_cookie_name}"
        return self.access_cookie_name

    @property
    def refresh_cookie(self) -> str:
        return (
            f"__Host-{self.refresh_cookie_name}"
            if self.cookie_host_prefix
            else self.refresh_cookie_name
        )

    @property
    def caller_cookie(self) -> str:
        return (
            f"__Host-{self.caller_cookie_name}"
            if self.cookie_host_prefix
            else self.caller_cookie_name
        )

    @field_validator("internal_allowed_cidrs")
    @classmethod
    def _valid_cidrs(cls, value: list[str]) -> list[str]:
        for item in value:
            try:
                ipaddress.ip_network(item, strict=False)
            except ValueError as exc:
                raise ValueError(f"invalid CIDR: {item}") from exc
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.is_production:
            jwt_secret = self.jwt_secret.get_secret_value()
            hmac_secret = self.internal_hmac_secret.get_secret_value()
            if len(jwt_secret) < 32 or jwt_secret.lower() in {"secret", "changeme"}:
                raise ValueError("TRIAVOZ_JWT_SECRET must be >= 32 random characters")
            if hmac_secret.startswith("change-me") or len(hmac_secret) < 32:
                raise ValueError("TRIAVOZ_INTERNAL_HMAC_SECRET must be >= 32 random characters")
            if not self.cookie_secure:
                raise ValueError("TRIAVOZ_COOKIE_SECURE must be true in production")
            if self.cookie_samesite == "none":
                raise ValueError("SameSite=None is not accepted; use the same-origin proxy")
            if "*" in self.cors_origins:
                raise ValueError("CORS wildcard is forbidden (credentials are enabled)")
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("CORS origins must use HTTPS in production")
            if (
                "change-me" in self.database_url_app
                or "://triavoz_owner:" in self.database_url_app
                or "://triavoz_owner@" in self.database_url_app
                or "://postgres:" in self.database_url_app
                or "://postgres@" in self.database_url_app
            ):
                raise ValueError("TRIAVOZ_DATABASE_URL_APP must point at the runtime role")
            if self.livekit_api_key == "devkey" or (
                self.livekit_api_secret.get_secret_value() == "secret"
            ):
                raise ValueError("LiveKit API key/secret must not be the dev defaults")
            # __Host- cookies require Secure + Path=/; production always satisfies both.
            self.cookie_host_prefix = True
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
