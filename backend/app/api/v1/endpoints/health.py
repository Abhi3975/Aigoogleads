"""Health, readiness & liveness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.db import ping_database
from app.core.logging import get_logger
from app.schemas.common import HealthResponse, ReadinessResponse

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Liveness check — the process is up and serving requests."""
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness() -> ReadinessResponse:
    """Readiness check — verifies critical dependencies (database) are reachable."""
    checks: dict[str, str] = {}

    try:
        await ping_database()
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - exercised only on outage
        logger.warning("readiness_db_failed", error=str(exc))
        checks["database"] = "error"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return ReadinessResponse(status=overall, checks=checks)
