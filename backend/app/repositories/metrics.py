"""Metrics repositories."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
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


class DailyPerformanceReportRepository(BaseRepository[DailyPerformanceReport]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DailyPerformanceReport, session)
