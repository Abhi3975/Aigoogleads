"""AI multi-agent system tests.

Real LLM calls need an API key, so we inject a deterministic fake provider and
a fake Google Ads client. This verifies the full orchestration end-to-end:
structured outputs, decision/step logging, memory, tool use, and execution.
"""

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
from app.schemas.agents import (
    AdCopyOutput,
    AnalyticsOutput,
    CampaignTheme,
    KeywordGroup,
    KeywordItem,
    KeywordResearchOutput,
    MatchType,
    Recommendation,
    RecommendationOutput,
    RecommendationType,
    ResponsiveSearchAd,
    RiskLevel,
    StrategyOutput,
)

API = "/api/v1"
CUSTOMER_ID = "1234567890"


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------
class _FakeProvider(LLMProvider):
    """Returns canned, valid structured outputs keyed by schema."""

    def __init__(self) -> None:
        self._registry = {
            "StrategyOutput": StrategyOutput(
                summary="Drive qualified leads within budget.",
                objective="Lead generation",
                recommended_daily_budget=33.0,
                target_cpa=20.0,
                target_roas=4.0,
                campaign_themes=[CampaignTheme(name="Brand", description="Brand terms")],
                reasoning="Budget split across brand and non-brand.",
            ),
            "KeywordResearchOutput": KeywordResearchOutput(
                groups=[
                    KeywordGroup(
                        ad_group_name="Brand",
                        keywords=[KeywordItem(text="acme crm", match_type=MatchType.PHRASE)],
                        negative_keywords=["free"],
                    )
                ],
                reasoning="Tight themes for quality score.",
            ),
            "AdCopyOutput": AdCopyOutput(
                ads=[
                    ResponsiveSearchAd(
                        ad_group_name="Brand",
                        headlines=["Acme CRM", "Try Acme CRM", "Close More Deals"],
                        descriptions=["The CRM teams love.", "Start free today."],
                        final_url="https://acme.example.com",
                    )
                ],
                reasoning="Benefit-led headlines.",
            ),
            "AnalyticsOutput": AnalyticsOutput(
                summary="Spend efficient; one campaign underperforming.",
                insights=["ROAS 8.0 overall"],
                anomalies=[],
                reasoning="Derived from 30-day metrics.",
            ),
            "RecommendationOutput": RecommendationOutput(
                summary="Increase budget on the top performer.",
                recommendations=[
                    Recommendation(
                        type=RecommendationType.ADJUST_BUDGET,
                        target="111",
                        rationale="High ROAS, budget-limited.",
                        expected_impact="+15% conversions",
                        risk_level=RiskLevel.LOW,
                        confidence=0.9,
                        current_value=10.0,
                        proposed_value=15.0,
                    )
                ],
                reasoning="Reallocate toward efficiency.",
            ),
        }

    async def complete_structured(self, *, system, user, schema, temperature=0.4):
        instance = self._registry[schema.__name__]
        return StructuredResult(data=instance, raw="{}", usage=Usage(100, 50, 150))


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
                        conversions=5,
                        conversions_value=200.0,
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


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
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


async def _seed_connection_and_account(db_engine: AsyncEngine, org_id: str) -> None:
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
                descriptive_name="Test Account",
                is_manager=False,
            )
        )
        await session.commit()


_BUSINESS = {
    "business_name": "Acme CRM",
    "industry": "SaaS",
    "description": "A CRM for small sales teams.",
    "monthly_budget": 1000.0,
    "goals": ["leads"],
    "target_locations": ["United States"],
}


# --------------------------------------------------------------------------
# Campaign planning workflow
# --------------------------------------------------------------------------
async def test_ai_not_configured_without_provider(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/plan", headers=headers, json=_BUSINESS
    )
    assert resp.status_code == 422  # AI provider not configured


async def test_campaign_plan_workflow(client: AsyncClient, fake_llm: None) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/plan", headers=headers, json=_BUSINESS
    )
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert run["status"] == "completed"
    assert run["total_tokens"] == 450  # 3 agents x 150

    # Structured aggregate output
    assert run["output"]["strategy"]["objective"] == "Lead generation"
    assert run["output"]["keywords"]["groups"][0]["ad_group_name"] == "Brand"
    assert run["output"]["ad_copy"]["ads"][0]["final_url"].startswith("https://")

    # Decision log: one step per specialist, in order, with reasoning
    steps = run["steps"]
    assert [s["agent_name"] for s in steps] == [
        "campaign_strategy",
        "keyword_research",
        "ad_copy",
    ]
    assert all(s["reasoning"] for s in steps)

    # Memory persisted the business profile
    mem = await client.get(
        f"{API}/organizations/{org_id}/ai/memory/business_profile", headers=headers
    )
    assert mem.status_code == 200
    assert any(e["key"] == "current" for e in mem.json())


async def test_runs_list_and_detail(client: AsyncClient, fake_llm: None) -> None:
    headers, org_id = await _register_owner(client)
    created = await client.post(
        f"{API}/organizations/{org_id}/ai/plan", headers=headers, json=_BUSINESS
    )
    run_id = created.json()["id"]

    listing = await client.get(f"{API}/organizations/{org_id}/ai/runs", headers=headers)
    assert listing.status_code == 200
    assert any(r["id"] == run_id for r in listing.json())

    detail = await client.get(f"{API}/organizations/{org_id}/ai/runs/{run_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["steps"]) == 3


# --------------------------------------------------------------------------
# Optimization workflow (tools + execution)
# --------------------------------------------------------------------------
async def test_optimization_requires_connection(client: AsyncClient, fake_llm: None) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/optimize",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert resp.status_code == 404  # not connected


async def test_optimization_with_auto_execute(
    client: AsyncClient, db_engine: AsyncEngine, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection_and_account(db_engine, org_id)

    resp = await client.post(
        f"{API}/organizations/{org_id}/ai/optimize",
        headers=headers,
        json={"customer_id": CUSTOMER_ID, "date_range": "LAST_30_DAYS", "auto_execute": True},
    )
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert run["status"] == "completed"

    # Supervisor (data gather) + analytics + recommendation + execution
    agent_names = [s["agent_name"] for s in run["steps"]]
    assert agent_names == ["supervisor", "analytics", "recommendation", "execution"]

    # The data-gathering step recorded tool calls
    gather = run["steps"][0]
    assert any(tc["tool"] == "get_metrics" for tc in gather["tool_calls"])

    # Execution applied the budget change via the Google Ads tool
    execution = run["output"]["execution"]
    assert execution["applied"][0]["status"] == "applied"
    assert execution["applied"][0]["tool"] == "update_budget"
