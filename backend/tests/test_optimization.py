"""Autonomous optimization engine tests (safety, loop, policy, notifications)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.agents.llm.base import LLMProvider, StructuredResult, Usage
from app.agents.llm.provider import reset_provider, set_provider
from app.core.security import encrypt_secret
from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection
from app.models.optimization import OptimizationPolicy
from app.schemas.agents import (
    AnalyticsOutput,
    Recommendation,
    RecommendationOutput,
    RecommendationType,
    RiskLevel,
)
from app.services.safety import SafetyEngine
from app.worker.jobs import find_optimization_targets

API = "/api/v1"
CUSTOMER_ID = "1234567890"


def _policy(**overrides: object) -> OptimizationPolicy:
    defaults = dict(
        organization_id=uuid.uuid4(),
        enabled=True,
        auto_execute=True,
        max_budget_increase_pct=20,
        max_budget_decrease_pct=30,
        max_bid_change_pct=25,
        min_days_active=7,
        min_clicks_required=100,
        min_keyword_clicks=100,
        min_keyword_days=14,
        min_confidence=0.6,
        date_range="LAST_30_DAYS",
    )
    defaults.update(overrides)
    return OptimizationPolicy(**defaults)


def _rec(type_: RecommendationType, **kw: object) -> Recommendation:
    base = dict(
        target="c1", rationale="r", expected_impact="i", risk_level=RiskLevel.LOW, confidence=0.9
    )
    base.update(kw)
    return Recommendation(type=type_, **base)  # type: ignore[arg-type]


# ==========================================================================
# Safety engine (unit)
# ==========================================================================
def test_budget_increase_clamped_to_cap() -> None:
    engine = SafetyEngine(_policy())
    rec = _rec(RecommendationType.ADJUST_BUDGET, current_value=100, proposed_value=200)
    d = engine.evaluate([rec], context={"c1": {"budget": 100}})[0]
    assert d.approved and d.adjusted_value == 120.0  # +100% clamped to +20%


def test_budget_decrease_clamped_to_cap() -> None:
    engine = SafetyEngine(_policy())
    rec = _rec(RecommendationType.ADJUST_BUDGET, current_value=100, proposed_value=10)
    d = engine.evaluate([rec], context={"c1": {"budget": 100}})[0]
    assert d.approved and d.adjusted_value == 70.0  # -90% clamped to -30%


def test_low_confidence_rejected() -> None:
    engine = SafetyEngine(_policy())
    rec = _rec(
        RecommendationType.ADJUST_BUDGET, confidence=0.3, current_value=100, proposed_value=110
    )
    d = engine.evaluate([rec], context={"c1": {"budget": 100}})[0]
    assert not d.approved and "confidence" in d.reason


def test_pause_blocked_by_min_clicks() -> None:
    engine = SafetyEngine(_policy())
    rec = _rec(RecommendationType.PAUSE_CAMPAIGN)
    d = engine.evaluate([rec], context={"c1": {"clicks": 10}})[0]
    assert not d.approved and "clicks" in d.reason


def test_pause_allowed_with_enough_data() -> None:
    engine = SafetyEngine(_policy())
    rec = _rec(RecommendationType.PAUSE_CAMPAIGN)
    d = engine.evaluate([rec], context={"c1": {"clicks": 500, "days_active": 30}})[0]
    assert d.approved


def test_unsupported_action_rejected() -> None:
    engine = SafetyEngine(_policy())
    d = engine.evaluate([_rec(RecommendationType.ADD_KEYWORD)], context={})[0]
    assert not d.approved


# ==========================================================================
# Loop + endpoints (fakes)
# ==========================================================================
class _FakeProvider(LLMProvider):
    async def complete_structured(self, *, system, user, schema, temperature=0.4):
        if schema.__name__ == "AnalyticsOutput":
            data = AnalyticsOutput(
                summary="Campaign 111 spends with zero conversions.",
                insights=["High spend, no conversions"],
                anomalies=["campaign 111"],
                reasoning="30-day snapshot.",
            )
        else:
            data = RecommendationOutput(
                summary="Scale budget on the efficient campaign.",
                recommendations=[
                    Recommendation(
                        type=RecommendationType.ADJUST_BUDGET,
                        target="111",
                        rationale="Efficient, budget limited.",
                        expected_impact="+conversions",
                        risk_level=RiskLevel.LOW,
                        confidence=0.9,
                        current_value=10,
                        proposed_value=15,
                    ),
                    Recommendation(
                        type=RecommendationType.PAUSE_CAMPAIGN,
                        target="111",
                        rationale="No conversions.",
                        expected_impact="save spend",
                        risk_level=RiskLevel.MEDIUM,
                        confidence=0.9,
                    ),
                ],
                reasoning="Reallocate toward efficiency.",
            )
        return StructuredResult(data=data, raw="{}", usage=Usage(80, 40, 120))


class _FakeAdsWrapper:
    def __init__(self, **_: object) -> None:
        pass

    def search(self, customer_id: str, query: str) -> list[object]:
        if "metrics.impressions" in query:
            return [
                SimpleNamespace(
                    campaign=SimpleNamespace(id=111, name="Brand"),
                    metrics=SimpleNamespace(
                        impressions=1000,
                        clicks=50,
                        cost_micros=25_000_000,
                        conversions=0,
                        conversions_value=0,
                        ctr=0.05,
                        average_cpc=500_000,
                    ),
                )
            ]
        return [
            SimpleNamespace(
                campaign=SimpleNamespace(
                    id=111,
                    name="Brand",
                    status="ENABLED",
                    advertising_channel_type="SEARCH",
                    bidding_strategy_type="MANUAL_CPC",
                ),
                campaign_budget=SimpleNamespace(amount_micros=10_000_000),
            )
        ]

    def update_campaign_budget(self, *, customer_id, campaign_id, daily_budget):
        return {"campaign_id": campaign_id, "daily_budget": str(daily_budget)}

    def set_campaign_status(self, *, customer_id, campaign_id, status):
        return {"campaign_id": campaign_id, "status": status}


@pytest.fixture
def fake_llm() -> None:
    set_provider(_FakeProvider())
    yield
    reset_provider()


@pytest.fixture
def fake_ads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.integrations.google_ads.client.create_wrapper",
        lambda **kwargs: _FakeAdsWrapper(**kwargs),
    )


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
        conn = GoogleAdsConnection(
            organization_id=uuid.UUID(org_id),
            refresh_token_encrypted=encrypt_secret("fake-refresh"),
            scopes="ads",
            status="active",
        )
        session.add(conn)
        await session.flush()
        session.add(
            GoogleAdsAccount(
                connection_id=conn.id,
                organization_id=uuid.UUID(org_id),
                customer_id=CUSTOMER_ID,
                descriptive_name="Test",
                is_manager=False,
            )
        )
        await session.commit()


async def test_policy_get_and_update(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    got = await client.get(f"{API}/organizations/{org_id}/optimization/policy", headers=headers)
    assert got.status_code == 200
    assert got.json()["max_budget_increase_pct"] == 20.0

    patched = await client.patch(
        f"{API}/organizations/{org_id}/optimization/policy",
        headers=headers,
        json={"enabled": True, "auto_execute": True, "max_budget_increase_pct": 10},
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] is True
    assert patched.json()["max_budget_increase_pct"] == 10.0


async def test_optimization_loop_applies_and_audits(
    client: AsyncClient, db_engine: AsyncEngine, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)

    resp = await client.post(
        f"{API}/organizations/{org_id}/optimization/run",
        headers=headers,
        json={"customer_id": CUSTOMER_ID, "auto_execute": True},
    )
    assert resp.status_code == 201, resp.text
    summary = resp.json()
    assert summary["applied"] == 1  # budget change (clamped)
    assert summary["rejected"] == 1  # pause blocked by min clicks

    # Audit log
    budget_log = next(log for log in summary["logs"] if log["action_type"] == "adjust_budget")
    assert budget_log["status"] == "executed"
    assert budget_log["previous_value"] == 10.0
    assert budget_log["new_value"] == 12.0  # +20% cap
    assert budget_log["explanation"]

    # Notification created for the applied action
    notes = await client.get(f"{API}/organizations/{org_id}/notifications", headers=headers)
    assert notes.status_code == 200
    assert any(n["type"] == "optimization" for n in notes.json())


async def test_notifications_read_flow(
    client: AsyncClient, db_engine: AsyncEngine, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)
    await client.post(
        f"{API}/organizations/{org_id}/optimization/run",
        headers=headers,
        json={"customer_id": CUSTOMER_ID, "auto_execute": True},
    )
    count = await client.get(
        f"{API}/organizations/{org_id}/notifications/unread-count", headers=headers
    )
    assert count.json()["unread"] >= 1

    all_read = await client.post(
        f"{API}/organizations/{org_id}/notifications/read-all", headers=headers
    )
    assert all_read.status_code == 200
    after = await client.get(
        f"{API}/organizations/{org_id}/notifications/unread-count", headers=headers
    )
    assert after.json()["unread"] == 0


async def test_find_optimization_targets_respects_enabled_flag(
    client: AsyncClient, db_engine: AsyncEngine
) -> None:
    _, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    # No policy / disabled => no targets.
    async with factory() as session:
        assert await find_optimization_targets(session) == []
        session.add(OptimizationPolicy(organization_id=uuid.UUID(org_id), enabled=True))
        await session.commit()

    async with factory() as session:
        targets = await find_optimization_targets(session)
    assert (uuid.UUID(org_id), CUSTOMER_ID) in targets
