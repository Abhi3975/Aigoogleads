"""Metrics repositories."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import CampaignMetric, DailyPerformanceReport
from app.repositories.base import BaseRepository


class CampaignMetricRepository(BaseRepository[CampaignMetric]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CampaignMetric, session)

    async def upsert_snapshot(
        self,
        *,
        organization_id: uuid.UUID,
        customer_id: str,
        campaign_id: str,
        day: date,
        values: dict[str, Any],
    ) -> CampaignMetric:
        stmt = select(CampaignMetric).where(
            CampaignMetric.organization_id == organization_id,
            CampaignMetric.customer_id == customer_id,
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.date == day,
        )
        existing = (await self.session.execute(stmt)).scalars().first()
        if existing is not None:
            return await self.update(existing, **values)
        return await self.create(
            organization_id=organization_id,
            customer_id=customer_id,
            campaign_id=campaign_id,
            date=day,
            **values,
        )

    async def list_recent(
        self, organization_id: uuid.UUID, customer_id: str, *, limit: int = 100
    ) -> list[CampaignMetric]:
        stmt = (
            select(CampaignMetric)
            .where(
                CampaignMetric.organization_id == organization_id,
                CampaignMetric.customer_id == customer_id,
            )
            .order_by(CampaignMetric.date.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_per_campaign(
        self, organization_id: uuid.UUID, customer_id: str | None = None
    ) -> list[CampaignMetric]:
        """The most recent snapshot for each campaign (org- or account-scoped)."""
        latest = select(
            CampaignMetric.campaign_id,
            func.max(CampaignMetric.date).label("max_date"),
        ).where(CampaignMetric.organization_id == organization_id)
        if customer_id is not None:
            latest = latest.where(CampaignMetric.customer_id == customer_id)
        latest = latest.group_by(CampaignMetric.campaign_id).subquery()

        stmt = (
            select(CampaignMetric)
            .join(
                latest,
                (CampaignMetric.campaign_id == latest.c.campaign_id)
                & (CampaignMetric.date == latest.c.max_date),
            )
            .where(CampaignMetric.organization_id == organization_id)
        )
        if customer_id is not None:
            stmt = stmt.where(CampaignMetric.customer_id == customer_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def daily_totals(
        self, organization_id: uuid.UUID, customer_id: str | None = None, *, limit: int = 90
    ) -> list[tuple]:
        """Per-day aggregated totals across campaigns (newest first, capped)."""
        stmt = select(
            CampaignMetric.date,
            func.sum(CampaignMetric.cost).label("cost"),
            func.sum(CampaignMetric.clicks).label("clicks"),
            func.sum(CampaignMetric.impressions).label("impressions"),
            func.sum(CampaignMetric.conversions).label("conversions"),
            func.sum(CampaignMetric.conversions_value).label("conversions_value"),
        ).where(CampaignMetric.organization_id == organization_id)
        if customer_id is not None:
            stmt = stmt.where(CampaignMetric.customer_id == customer_id)
        stmt = stmt.group_by(CampaignMetric.date).order_by(CampaignMetric.date.desc()).limit(limit)
        return list((await self.session.execute(stmt)).all())


class DailyPerformanceReportRepository(BaseRepository[DailyPerformanceReport]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DailyPerformanceReport, session)
