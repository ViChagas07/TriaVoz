from __future__ import annotations

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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
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
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(internal_agent.router)
    app.include_router(api_v1_router)
    return app


app = create_app()
