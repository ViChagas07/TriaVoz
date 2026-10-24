from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from triavoz import __version__
from triavoz.config import get_settings
from triavoz.infrastructure.db.session import dispose_engine
from triavoz.interfaces.http import health, internal_agent
from triavoz.interfaces.http.api_v1.router import router as api_v1_router
from triavoz.interfaces.http.errors import register_exception_handlers
from triavoz.interfaces.http.middleware import register_request_middleware
from triavoz.observability.logging import configure_logging
from triavoz.observability.routes import router as observability_router
from triavoz.observability.sentry import init_sentry
from triavoz.observability.tracing import setup_from_settings

log = logging.getLogger("triavoz.startup")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    init_sentry(settings, service="triavoz-api")
    app = FastAPI(
        title="TriaVoz API",
        version=__version__,
        lifespan=lifespan,
        # Interactive docs only outside production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    register_request_middleware(app)
    if settings.is_production and not settings.trust_forwarded_for:
        log.warning(
            "TRIAVOZ_TRUST_FORWARDED_FOR is false in production: per-IP rate limits will "
            "collapse to the proxy address; enable it only behind a proxy that overwrites XFF"
        )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(observability_router)
    app.include_router(internal_agent.router)
    app.include_router(api_v1_router)
    setup_from_settings(app, settings)
    return app


app = create_app()
