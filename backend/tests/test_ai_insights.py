"""AI insight / learning-memory tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.services.ai_insights import AIInsightService

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


async def _seed(db_engine: AsyncEngine, org_id: str) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        svc = AIInsightService(session)
        await svc.record(
            organization_id=uuid.UUID(org_id),
            agent_name="optimization_engine",
            insight_type="optimization",
            observation="low importance learning",
            importance_score=0.2,
            confidence=0.5,
        )
        await svc.record(
            organization_id=uuid.UUID(org_id),
            agent_name="performance_analyzer",
            insight_type="performance",
            observation="high importance learning",
            importance_score=0.9,
            confidence=0.8,
        )
        await session.commit()


async def test_insights_ranked_by_importance(client: AsyncClient, db_engine: AsyncEngine) -> None:
    headers, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)

    resp = await client.get(f"{API}/organizations/{org_id}/ai/insights", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 2
    # Highest importance first (retrieval ranking).
    assert items[0]["observation"] == "high importance learning"
    assert items[0]["importance_score"] == 0.9


async def test_insights_filter_by_type(client: AsyncClient, db_engine: AsyncEngine) -> None:
    headers, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)

    resp = await client.get(
        f"{API}/organizations/{org_id}/ai/insights",
        params={"insight_type": "optimization"},
        headers=headers,
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["insight_type"] == "optimization"


async def test_insights_empty(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.get(f"{API}/organizations/{org_id}/ai/insights", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_importance_clamped(client: AsyncClient, db_engine: AsyncEngine) -> None:
    _, org_id = await _register_owner(client)
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        insight = await AIInsightService(session).record(
            organization_id=uuid.UUID(org_id),
            agent_name="x",
            insight_type="t",
            observation="o",
            importance_score=5.0,
            confidence=-1.0,
        )
        await session.commit()
    assert float(insight.importance_score) == 1.0
    assert float(insight.confidence) == 0.0
