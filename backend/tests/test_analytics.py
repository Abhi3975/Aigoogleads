"""Analytics aggregation tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.metrics import CampaignMetric

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


async def _seed_metrics(db_engine: AsyncEngine, org_id: str) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    today = datetime.now(UTC).date()
    async with factory() as session:
        session.add_all(
            [
                CampaignMetric(
                    organization_id=uuid.UUID(org_id),
                    customer_id="123",
                    campaign_id="111",
                    campaign_name="Brand",
                    date=today,
                    impressions=1000,
                    clicks=100,
                    cost=50,
                    conversions=10,
                    conversions_value=300,
                    ctr=0.1,
                    average_cpc=0.5,
                    cpa=5,
                    roas=6,
                ),
                CampaignMetric(
                    organization_id=uuid.UUID(org_id),
                    customer_id="123",
                    campaign_id="222",
                    campaign_name="Generic",
                    date=today,
                    impressions=2000,
                    clicks=100,
                    cost=100,
                    conversions=5,
                    conversions_value=100,
                    ctr=0.05,
                    average_cpc=1.0,
                    cpa=20,
                    roas=1,
                ),
                # An older snapshot for 111 that must be ignored by "latest".
                CampaignMetric(
                    organization_id=uuid.UUID(org_id),
                    customer_id="123",
                    campaign_id="111",
                    campaign_name="Brand",
                    date=today - timedelta(days=1),
                    impressions=1,
                    clicks=1,
                    cost=999,
                    conversions=0,
                    conversions_value=0,
                    ctr=0,
                    average_cpc=0,
                    cpa=0,
                    roas=0,
                ),
            ]
        )
        await session.commit()


async def test_analytics_summary(client: AsyncClient, db_engine: AsyncEngine) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_metrics(db_engine, org_id)

    resp = await client.get(f"{API}/organizations/{org_id}/analytics/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Latest snapshots only: cost 50 + 100 = 150 (old 999 ignored).
    assert body["totals"]["cost"] == 150.0
    assert body["totals"]["conversions"] == 15.0
    assert body["totals"]["roas"] == round(400 / 150, 2)
    # Sorted by cost desc: Generic (100) before Brand (50).
    assert [c["campaign_id"] for c in body["campaigns"]] == ["222", "111"]
    assert body["campaigns"][1]["cpa"] == 5.0  # Brand: 50 / 10


async def test_analytics_timeseries(client: AsyncClient, db_engine: AsyncEngine) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_metrics(db_engine, org_id)

    resp = await client.get(f"{API}/organizations/{org_id}/analytics/timeseries", headers=headers)
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 2  # two distinct days
    # Chronological order (oldest first).
    assert points[0]["date"] < points[1]["date"]


async def test_analytics_empty(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.get(f"{API}/organizations/{org_id}/analytics/summary", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["totals"]["cost"] == 0.0
    assert resp.json()["campaigns"] == []
