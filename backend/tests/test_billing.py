"""Usage tracking & plan-limit enforcement tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.usage import UsageRecord
from app.services.usage import current_period

API = "/api/v1"

# A valid BusinessContext body for POST /ai/plan (the quota-gated endpoint).
_BUSINESS = {
    "business_name": "Acme",
    "industry": "SaaS",
    "description": "A CRM for small teams.",
    "monthly_budget": 1000,
}


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


async def _seed_usage(db_engine: AsyncEngine, org_id: str, feature: str, count: int) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            UsageRecord(
                organization_id=uuid.UUID(org_id),
                feature=feature,
                period=current_period(),
                count=count,
            )
        )
        await session.commit()


async def test_billing_status_defaults_to_free(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.get(f"{API}/organizations/{org_id}/billing/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "free"
    assert body["limits"]["monthly_ai_runs"] == 10


async def test_list_plans(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.get(f"{API}/organizations/{org_id}/billing/plans", headers=headers)
    assert resp.status_code == 200
    plans = {p["plan"] for p in resp.json()}
    assert plans == {"free", "starter", "growth", "enterprise"}


async def test_quota_allows_when_under_limit(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    # Under the free limit -> the quota guard passes; the handler then fails only
    # because no AI provider is configured (422), proving the guard let it through.
    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/plan", headers=headers, json=_BUSINESS
    )
    assert resp.status_code == 422  # ai_not_configured, NOT 402


async def test_quota_blocks_at_limit(client: AsyncClient, db_engine: AsyncEngine) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_usage(db_engine, org_id, "ai_run", 10)  # free plan monthly limit
    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/plan", headers=headers, json=_BUSINESS
    )
    assert resp.status_code == 402
    assert resp.json()["error"]["code"] == "plan_limit_exceeded"


async def test_upgrade_lifts_limit(client: AsyncClient, db_engine: AsyncEngine) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_usage(db_engine, org_id, "ai_run", 10)

    upgrade = await client.patch(
        f"{API}/organizations/{org_id}/billing/plan", headers=headers, json={"plan": "enterprise"}
    )
    assert upgrade.status_code == 200
    assert upgrade.json()["plan"] == "enterprise"
    assert upgrade.json()["limits"]["monthly_ai_runs"] == -1  # unlimited

    # Now the quota guard no longer blocks (falls through to 422 ai-not-configured).
    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/plan", headers=headers, json=_BUSINESS
    )
    assert resp.status_code == 422
