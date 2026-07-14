"""Analytics endpoints — aggregated performance KPIs & timeseries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentMembership, DbSession
from app.schemas.analytics import AnalyticsSummary, AnalyticsTimeseries
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/organizations/{organization_id}/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    customer_id: str | None = Query(default=None),
) -> AnalyticsSummary:
    """KPI summary + per-campaign performance (any member)."""
    return await AnalyticsService(session).summary(organization_id, customer_id)


@router.get("/timeseries", response_model=AnalyticsTimeseries)
async def analytics_timeseries(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    customer_id: str | None = Query(default=None),
) -> AnalyticsTimeseries:
    """Daily aggregated performance for trend charts (any member)."""
    return await AnalyticsService(session).timeseries(organization_id, customer_id)
