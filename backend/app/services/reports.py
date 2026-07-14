"""Performance reports service — aggregate stored metrics into daily reports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestMeta
from app.models.metrics import DailyPerformanceReport
from app.repositories.metrics import DailyPerformanceReportRepository
from app.services.metrics import MetricsService, metric_to_payload
from app.services.notification import NotificationService


class ReportsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.metrics = MetricsService(session)
        self.repo = DailyPerformanceReportRepository(session)

    async def generate(
        self,
        *,
        organization_id: uuid.UUID,
        customer_id: str,
        actor_user_id: uuid.UUID | None = None,
        meta: RequestMeta | None = None,
    ) -> DailyPerformanceReport:
        """Fetch + aggregate metrics into today's report (upserts, then notifies)."""
        stored = await self.metrics.fetch_and_store_campaigns(organization_id, customer_id)
        payloads = [metric_to_payload(m) for m in stored]
        cost = round(sum(p["cost"] for p in payloads), 2)
        conv_value = round(sum(p["conversions_value"] for p in payloads), 2)
        totals = {
            "campaigns": len(payloads),
            "cost": cost,
            "clicks": sum(p["clicks"] for p in payloads),
            "impressions": sum(p["impressions"] for p in payloads),
            "conversions": round(sum(p["conversions"] for p in payloads), 2),
            "conversions_value": conv_value,
            "roas": round(conv_value / cost, 2) if cost else 0.0,
        }
        summary = (
            f"{totals['campaigns']} campaigns · ${totals['cost']} spend · "
            f"{totals['conversions']} conversions · ROAS {totals['roas']}"
        )
        today = datetime.now(UTC).date()

        report = await self.repo.get_for_day(organization_id, customer_id, today)
        if report is not None:
            report = await self.repo.update(
                report, summary=summary, totals=totals, report={"campaigns": payloads}
            )
        else:
            report = await self.repo.create(
                organization_id=organization_id,
                customer_id=customer_id,
                date=today,
                summary=summary,
                totals=totals,
                report={"campaigns": payloads},
            )

        await NotificationService(self.session).create(
            organization_id=organization_id,
            type="report",
            title="Performance report generated",
            body=summary,
            data=totals,
        )
        await self.session.commit()
        return report

    async def list(
        self, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DailyPerformanceReport]:
        return await self.repo.list_for_org(organization_id, offset=offset, limit=limit)
