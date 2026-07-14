"""Google Ads metrics collection service — fetch and store historical metrics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import CampaignMetric
from app.repositories.metrics import CampaignMetricRepository
from app.services.google_ads import GoogleAdsService


class MetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ads = GoogleAdsService(session)
        self.repo = CampaignMetricRepository(session)

    async def fetch_and_store_campaigns(
        self, organization_id: uuid.UUID, customer_id: str, date_range: str = "LAST_30_DAYS"
    ) -> list[CampaignMetric]:
        metrics = await self.ads.get_campaign_metrics(organization_id, customer_id, date_range)
        today = datetime.now(UTC).date()
        stored: list[CampaignMetric] = []
        for m in metrics:
            cpa = round(m.cost / m.conversions, 2) if m.conversions else 0.0
            row = await self.repo.upsert_snapshot(
                organization_id=organization_id,
                customer_id=customer_id,
                campaign_id=m.campaign_id,
                day=today,
                values={
                    "campaign_name": m.campaign_name,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "cost": m.cost,
                    "conversions": m.conversions,
                    "conversions_value": m.conversions_value,
                    "ctr": m.ctr,
                    "average_cpc": m.average_cpc,
                    "cpa": cpa,
                    "roas": m.roas,
                    "metrics": m.model_dump(mode="json"),
                },
            )
            stored.append(row)
        await self.session.commit()
        return stored


def metric_to_payload(row: CampaignMetric) -> dict[str, Any]:
    return {
        "campaign_id": row.campaign_id,
        "campaign_name": row.campaign_name,
        "impressions": row.impressions,
        "clicks": row.clicks,
        "cost": float(row.cost),
        "conversions": float(row.conversions),
        "conversions_value": float(row.conversions_value),
        "ctr": float(row.ctr),
        "average_cpc": float(row.average_cpc),
        "cpa": float(row.cpa),
        "roas": float(row.roas),
    }
