"""Billing / plan endpoints (billing-ready; payment provider pluggable)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import CurrentMembership, DbSession, require_role
from app.core.exceptions import NotFoundError
from app.models.enums import OrgRole
from app.models.organization import Organization, OrganizationMembership
from app.schemas.billing import BillingStatus, PlanChange, PlanInfo
from app.services.usage import PLAN_LIMITS, UsageService

router = APIRouter(prefix="/organizations/{organization_id}/billing", tags=["billing"])


@router.get("/status", response_model=BillingStatus)
async def billing_status(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> BillingStatus:
    """Current plan, its limits, and this month's usage (any member)."""
    usage = UsageService(session)
    plan = await usage.get_plan(organization_id)
    return BillingStatus(
        plan=plan,
        limits=usage.limits_for(plan),
        usage=await usage.usage_summary(organization_id),
    )


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans(organization_id: uuid.UUID, membership: CurrentMembership) -> list[PlanInfo]:
    """List available plans and their limits (any member)."""
    return [PlanInfo(plan=name, limits=limits) for name, limits in PLAN_LIMITS.items()]


@router.patch("/plan", response_model=BillingStatus)
async def change_plan(
    organization_id: uuid.UUID,
    data: PlanChange,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.OWNER)),
) -> BillingStatus:
    """Change the organization's plan (owner only). Payment integration pluggable."""
    org = await session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    org.plan = data.plan
    await session.commit()

    usage = UsageService(session)
    return BillingStatus(
        plan=data.plan.value,
        limits=usage.limits_for(data.plan.value),
        usage=await usage.usage_summary(organization_id),
    )
