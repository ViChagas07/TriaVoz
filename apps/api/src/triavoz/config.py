"""Application settings. Secrets come ONLY from the environment (never hardcoded)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
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

    # Service-to-service auth between the voice worker and this API (HMAC-SHA256).
    internal_hmac_secret: SecretStr = SecretStr("change-me-dev-only")
    internal_hmac_tolerance_seconds: int = 60

    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
