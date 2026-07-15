"""Billing / plan endpoints (billing-ready; payment provider pluggable)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request

from app.api.deps import CurrentMembership, DbSession, require_role
from app.core.config import settings
from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.models.enums import OrgRole
from app.models.organization import Organization, OrganizationMembership
from app.schemas.billing import (
    BillingStatus,
    CheckoutRequest,
    CheckoutSession,
    PlanChange,
    PlanInfo,
)
from app.schemas.common import Message
from app.services.stripe_billing import StripeService
from app.services.usage import PLAN_LIMITS, UsageService

router = APIRouter(prefix="/organizations/{organization_id}/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/billing", tags=["billing"])


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


@router.post("/checkout", response_model=CheckoutSession)
async def create_checkout(
    organization_id: uuid.UUID,
    data: CheckoutRequest,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.OWNER)),
) -> CheckoutSession:
    """Create a Stripe Checkout session to upgrade the plan (owner only)."""
    service = StripeService(session)
    if not service.is_configured:
        raise ValidationError(
            "Billing checkout is not configured (Stripe).", error_code="billing_not_configured"
        )
    url = await service.create_checkout_session(
        organization_id=organization_id,
        plan=data.plan.value,
        success_url=f"{settings.FRONTEND_BASE_URL}/billing?upgraded=1",
        cancel_url=f"{settings.FRONTEND_BASE_URL}/billing",
    )
    return CheckoutSession(url=url)


@webhook_router.post("/webhook", response_model=Message)
async def stripe_webhook(
    request: Request,
    session: DbSession,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> Message:
    """Receive Stripe subscription lifecycle events and apply them to the plan."""
    service = StripeService(session)
    if not service.is_configured:
        raise ValidationError("Billing is not configured.", error_code="billing_not_configured")
    payload = await request.body()
    try:
        event = service.construct_event(payload, stripe_signature or "")
    except Exception as exc:
        # Invalid signature or malformed payload.
        raise UnauthorizedError("Invalid webhook signature.") from exc
    await service.apply_event(event)
    return Message(message="ok")
