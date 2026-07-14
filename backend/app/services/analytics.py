"""Analytics service — aggregates stored campaign metrics into KPI summaries."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.metrics import CampaignMetricRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    AnalyticsTimeseries,
    CampaignPerformance,
    KpiTotals,
    TimeseriesPoint,
)


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 2) if denominator else 0.0


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CampaignMetricRepository(session)

    async def summary(
        self, organization_id: uuid.UUID, customer_id: str | None = None
    ) -> AnalyticsSummary:
        rows = await self.repo.latest_per_campaign(organization_id, customer_id)
        campaigns: list[CampaignPerformance] = []
        impressions = clicks = 0
        cost = conversions = conversions_value = 0.0
        as_of = None

        for row in rows:
            row_cost = float(row.cost)
            row_conv = float(row.conversions)
            impressions += row.impressions
            clicks += row.clicks
            cost += row_cost
            conversions += row_conv
            conversions_value += float(row.conversions_value)
            as_of = max(as_of, row.date) if as_of else row.date
            campaigns.append(
                CampaignPerformance(
                    campaign_id=row.campaign_id,
                    campaign_name=row.campaign_name,
                    cost=round(row_cost, 2),
                    clicks=row.clicks,
                    conversions=round(row_conv, 2),
                    ctr=float(row.ctr),
                    cpa=_ratio(row_cost, row_conv),
                    roas=float(row.roas),
                )
            )

        totals = KpiTotals(
            impressions=impressions,
            clicks=clicks,
            cost=round(cost, 2),
            conversions=round(conversions, 2),
            conversions_value=round(conversions_value, 2),
            ctr=round(clicks / impressions, 4) if impressions else 0.0,
            average_cpc=_ratio(cost, clicks),
            cpa=_ratio(cost, conversions),
            roas=_ratio(conversions_value, cost),
            conversion_rate=round(conversions / clicks, 4) if clicks else 0.0,
        )
        campaigns.sort(key=lambda c: c.cost, reverse=True)
        return AnalyticsSummary(as_of=as_of, totals=totals, campaigns=campaigns)

    async def timeseries(
        self, organization_id: uuid.UUID, customer_id: str | None = None
    ) -> AnalyticsTimeseries:
        rows = await self.repo.daily_totals(organization_id, customer_id)
        points = [
            TimeseriesPoint(
                date=row.date,
                cost=round(float(row.cost), 2),
                clicks=int(row.clicks),
                conversions=round(float(row.conversions), 2),
                conversions_value=round(float(row.conversions_value), 2),
            )
            for row in reversed(rows)  # chronological order
        ]
        return AnalyticsTimeseries(points=points)
