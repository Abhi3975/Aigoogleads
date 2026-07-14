"""FastAPI application factory and ASGI entrypoint.

Run locally:   uv run uvicorn app.main:app --reload
Run in prod:   gunicorn app.main:app -k uvicorn.workers.UvicornWorker
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks."""
    configure_logging()
    logger.info(
        "application_startup",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )
    yield
    logger.info("application_shutdown")


def create_application() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- Middleware (outermost added last) ---
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Root-level liveness probe (used by Docker/Nginx health checks)
    @app.get("/health", tags=["health"], summary="Root liveness probe")
    async def root_health() -> dict[str, str]:
        return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}

    return app


app = create_application()
