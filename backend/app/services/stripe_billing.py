"""Stripe billing integration.

Creates Checkout Sessions for plan upgrades and applies subscription lifecycle
webhook events to the organization's plan. The Stripe SDK is imported lazily so
the app runs without it when billing is not configured.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.models.enums import OrgPlan
from app.models.organization import Organization

logger = get_logger(__name__)


def _price_for(plan: str) -> str | None:
    return {
        "starter": settings.STRIPE_PRICE_STARTER,
        "growth": settings.STRIPE_PRICE_GROWTH,
        "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
    }.get(plan) or None


class StripeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @property
    def is_configured(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY)

    async def create_checkout_session(
        self, *, organization_id: uuid.UUID, plan: str, success_url: str, cancel_url: str
    ) -> str:
        price = _price_for(plan)
        if price is None:
            raise ValidationError(f"No Stripe price configured for the '{plan}' plan.")

        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"organization_id": str(organization_id), "plan": plan},
            subscription_data={"metadata": {"organization_id": str(organization_id), "plan": plan}},
        )
        return str(session.url)

    def construct_event(self, payload: bytes, signature: str) -> dict[str, Any]:
        import stripe

        return stripe.Webhook.construct_event(  # type: ignore[no-any-return]
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )

    async def apply_event(self, event: dict[str, Any]) -> None:
        """Apply a subscription lifecycle event to the organization's plan."""
        event_type = event.get("type", "")
        obj = event.get("data", {}).get("object", {})

        if event_type in {"checkout.session.completed", "customer.subscription.updated"}:
            metadata = obj.get("metadata", {}) or {}
            org_id = metadata.get("organization_id")
            plan = metadata.get("plan")
            if org_id and plan:
                await self._set_plan(
                    uuid.UUID(org_id),
                    plan,
                    customer=obj.get("customer"),
                    subscription=obj.get("subscription") or obj.get("id"),
                )
        elif event_type == "customer.subscription.deleted":
            await self._downgrade_by_subscription(obj.get("id"))

    async def _set_plan(
        self,
        organization_id: uuid.UUID,
        plan: str,
        *,
        customer: str | None,
        subscription: str | None,
    ) -> None:
        org = await self.session.get(Organization, organization_id)
        if org is None:
            return
        try:
            org.plan = OrgPlan(plan)
        except ValueError:
            logger.warning("stripe_unknown_plan", plan=plan)
            return
        if customer:
            org.stripe_customer_id = customer
        if subscription:
            org.stripe_subscription_id = subscription
        await self.session.commit()

    async def _downgrade_by_subscription(self, subscription_id: str | None) -> None:
        if not subscription_id:
            return
        stmt = select(Organization).where(Organization.stripe_subscription_id == subscription_id)
        org = (await self.session.execute(stmt)).scalars().first()
        if org is not None:
            org.plan = OrgPlan.FREE
            await self.session.commit()
