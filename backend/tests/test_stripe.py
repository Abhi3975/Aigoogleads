"""Stripe billing tests (webhook apply logic + checkout gating).

Live Stripe API calls require credentials; here we test the parts we own: the
subscription-event → plan mapping and the not-configured checkout response.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.enums import OrgPlan
from app.models.organization import Organization
from app.services.stripe_billing import StripeService

API = "/api/v1"


async def _register_owner(client: AsyncClient) -> tuple[dict[str, str], str]:
    email = f"owner_{uuid.uuid4().hex[:10]}@example.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": "Owner"},
    )
    token = reg.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    org_id = (await client.get(f"{API}/organizations", headers=headers)).json()[0]["id"]
    return headers, org_id


async def test_checkout_session_completed_sets_plan(
    client: AsyncClient, db_engine: AsyncEngine
) -> None:
    headers, org_id = await _register_owner(client)
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        await StripeService(session).apply_event(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer": "cus_123",
                        "subscription": "sub_123",
                        "metadata": {"organization_id": org_id, "plan": "starter"},
                    }
                },
            }
        )

    status = await client.get(f"{API}/organizations/{org_id}/billing/status", headers=headers)
    assert status.json()["plan"] == "starter"


async def test_subscription_deleted_downgrades_to_free(
    client: AsyncClient, db_engine: AsyncEngine
) -> None:
    headers, org_id = await _register_owner(client)
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        org = await session.get(Organization, uuid.UUID(org_id))
        assert org is not None
        org.plan = OrgPlan.GROWTH
        org.stripe_subscription_id = "sub_del"
        await session.commit()

    async with factory() as session:
        await StripeService(session).apply_event(
            {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_del"}}}
        )

    status = await client.get(f"{API}/organizations/{org_id}/billing/status", headers=headers)
    assert status.json()["plan"] == "free"


async def test_checkout_not_configured_returns_422(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/billing/checkout",
        headers=headers,
        json={"plan": "starter"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "billing_not_configured"
