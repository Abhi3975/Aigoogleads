"""Async job functions backing the Celery tasks.

Each job manages its own async DB session. Kept free of Celery imports so they
can be unit-tested directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection
from app.models.metrics import DailyPerformanceReport
from app.models.optimization import OptimizationPolicy
from app.services.metrics import MetricsService, metric_to_payload
from app.services.notification import NotificationService
from app.services.optimization_engine import OptimizationEngine

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# Target discovery (pure queries, unit-testable)
# --------------------------------------------------------------------------
async def find_metrics_targets(session: AsyncSession) -> list[tuple[uuid.UUID, str]]:
    """(org_id, customer_id) for every linked non-manager account with an
    active connection."""
    stmt = (
        select(GoogleAdsAccount.organization_id, GoogleAdsAccount.customer_id)
        .join(GoogleAdsConnection, GoogleAdsConnection.id == GoogleAdsAccount.connection_id)
        .where(
            GoogleAdsConnection.status == "active",
            GoogleAdsAccount.is_manager.is_(False),
        )
    )
    rows = await session.execute(stmt)
    return [(row[0], row[1]) for row in rows.all()]


async def find_optimization_targets(session: AsyncSession) -> list[tuple[uuid.UUID, str]]:
    """Metrics targets restricted to organizations that enabled autonomous
    optimization."""
    stmt = (
        select(GoogleAdsAccount.organization_id, GoogleAdsAccount.customer_id)
        .join(GoogleAdsConnection, GoogleAdsConnection.id == GoogleAdsAccount.connection_id)
        .join(
            OptimizationPolicy,
            OptimizationPolicy.organization_id == GoogleAdsAccount.organization_id,
        )
        .where(
            GoogleAdsConnection.status == "active",
            GoogleAdsAccount.is_manager.is_(False),
            OptimizationPolicy.enabled.is_(True),
        )
    )
    rows = await session.execute(stmt)
    return [(row[0], row[1]) for row in rows.all()]


# --------------------------------------------------------------------------
# Per-target jobs
# --------------------------------------------------------------------------
async def fetch_metrics_job(
    session: AsyncSession, organization_id: uuid.UUID, customer_id: str
) -> int:
    stored = await MetricsService(session).fetch_and_store_campaigns(organization_id, customer_id)
    return len(stored)


async def optimize_account_job(
    session: AsyncSession, organization_id: uuid.UUID, customer_id: str
) -> dict:
    try:
        return await OptimizationEngine(session).run(
            organization_id=organization_id, customer_id=customer_id
        )
    except AppError as exc:
        # e.g. AI not configured / no connection — skip gracefully.
        logger.info("optimization_skipped", organization_id=str(organization_id), reason=str(exc))
        return {"skipped": str(exc)}


async def generate_report_job(
    session: AsyncSession, organization_id: uuid.UUID, customer_id: str
) -> uuid.UUID:
    """Aggregate stored metrics into a daily performance report + notification."""
    stored = await MetricsService(session).fetch_and_store_campaigns(organization_id, customer_id)
    payloads = [metric_to_payload(m) for m in stored]
    totals = {
        "campaigns": len(payloads),
        "cost": round(sum(p["cost"] for p in payloads), 2),
        "clicks": sum(p["clicks"] for p in payloads),
        "conversions": round(sum(p["conversions"] for p in payloads), 2),
        "conversions_value": round(sum(p["conversions_value"] for p in payloads), 2),
    }
    totals["roas"] = round(totals["conversions_value"] / totals["cost"], 2) if totals["cost"] else 0
    summary = (
        f"{totals['campaigns']} campaigns · ${totals['cost']} spend · "
        f"{totals['conversions']} conversions · ROAS {totals['roas']}"
    )
    report = DailyPerformanceReport(
        organization_id=organization_id,
        customer_id=customer_id,
        date=datetime.now(UTC).date(),
        summary=summary,
        totals=totals,
        report={"campaigns": payloads},
    )
    session.add(report)
    await NotificationService(session).create(
        organization_id=organization_id,
        type="report",
        title="Daily performance report",
        body=summary,
        data=totals,
    )
    await session.commit()
    return report.id
