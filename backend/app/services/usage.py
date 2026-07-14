"""Usage metering + plan-limit enforcement.

Per-plan quotas are checked before metered actions and counted per calendar
month. ``-1`` denotes unlimited.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LimitExceededError
from app.models.organization import Organization
from app.models.usage import UsageRecord

# Limits keyed by OrgPlan value. -1 = unlimited.
PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": {"monthly_ai_runs": 10, "max_google_ads_accounts": 1, "max_active_campaigns": 3},
    "starter": {"monthly_ai_runs": 200, "max_google_ads_accounts": 5, "max_active_campaigns": 25},
    "growth": {"monthly_ai_runs": 1000, "max_google_ads_accounts": 20, "max_active_campaigns": 100},
    "enterprise": {
        "monthly_ai_runs": -1,
        "max_google_ads_accounts": -1,
        "max_active_campaigns": -1,
    },
}

# Maps a metered feature to the plan-limit key that governs it.
FEATURE_LIMIT_KEY: dict[str, str] = {
    "ai_run": "monthly_ai_runs",
}


def current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


class UsageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_plan(self, organization_id: uuid.UUID) -> str:
        stmt = select(Organization.plan).where(Organization.id == organization_id)
        plan = (await self.session.execute(stmt)).scalar_one_or_none()
        return plan.value if plan is not None else "free"

    def limits_for(self, plan: str) -> dict[str, int]:
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    async def get_count(
        self, organization_id: uuid.UUID, feature: str, period: str | None = None
    ) -> int:
        stmt = select(UsageRecord.count).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.feature == feature,
            UsageRecord.period == (period or current_period()),
        )
        return int((await self.session.execute(stmt)).scalar_one_or_none() or 0)

    async def _increment(self, organization_id: uuid.UUID, feature: str, period: str) -> None:
        stmt = select(UsageRecord).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.feature == feature,
            UsageRecord.period == period,
        )
        record = (await self.session.execute(stmt)).scalars().first()
        if record is None:
            record = UsageRecord(
                organization_id=organization_id, feature=feature, period=period, count=1
            )
            self.session.add(record)
        else:
            record.count += 1
        await self.session.flush()

    async def consume(self, organization_id: uuid.UUID, feature: str) -> None:
        """Check the plan limit for ``feature`` and, if within it, count one use."""
        period = current_period()
        limit_key = FEATURE_LIMIT_KEY.get(feature)
        if limit_key is not None:
            plan = await self.get_plan(organization_id)
            limit = self.limits_for(plan).get(limit_key, -1)
            if limit >= 0:
                used = await self.get_count(organization_id, feature, period)
                if used >= limit:
                    raise LimitExceededError(
                        f"Monthly limit reached for '{feature}' on the {plan} plan "
                        f"({used}/{limit}). Upgrade to continue.",
                        details={"feature": feature, "used": used, "limit": limit, "plan": plan},
                    )
        await self._increment(organization_id, feature, period)

    async def usage_summary(self, organization_id: uuid.UUID) -> dict[str, int]:
        period = current_period()
        stmt = select(UsageRecord.feature, UsageRecord.count).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.period == period,
        )
        rows = (await self.session.execute(stmt)).all()
        return {row.feature: int(row.count) for row in rows}
