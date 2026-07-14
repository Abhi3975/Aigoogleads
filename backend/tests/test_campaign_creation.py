"""Autonomous campaign-creation tests (backend).

Uses an injected fake LLM provider and a fake Google Ads client to verify the
full workflow: onboarding, website analysis, AI planning, blueprint assembly
with RSA validation, execution with per-action logs, and safety controls.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.agents.llm.base import LLMProvider, StructuredResult, Usage
from app.agents.llm.provider import reset_provider, set_provider
from app.core.security import encrypt_secret
from app.integrations.website import WebsiteContent
from app.models.campaign import CampaignBlueprint
from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection
from app.schemas.agents import MatchType
from app.schemas.campaign import (
    AdCreativeOutput,
    AdExtensions,
    AdGroupKeywords,
    AdGroupPlan,
    CampaignStrategyPlan,
    CampaignType,
    KeywordIntent,
    KeywordPlanOutput,
    KeywordSpec,
    RSACreative,
    Sitelink,
    WebsiteAnalysisOutput,
)
from app.services.campaign_assembler import assemble_blueprint

API = "/api/v1"
CUSTOMER_ID = "1234567890"

_HEADLINES = [f"Headline {i}" for i in range(1, 16)]  # 15 valid (<=30 chars)
_DESCRIPTIONS = [f"Great description number {i}" for i in range(1, 5)]  # 4 valid


def _strategy() -> CampaignStrategyPlan:
    return CampaignStrategyPlan(
        campaign_name="Acme CRM - Search",
        campaign_type=CampaignType.SEARCH,
        objective="Lead generation",
        recommended_daily_budget=50.0,
        bidding_strategy="MANUAL_CPC",
        location_targeting=["United States"],
        audience_targeting="SMB owners",
        ad_groups=[
            AdGroupPlan(name="Brand", theme="brand terms"),
            AdGroupPlan(name="CRM Software", theme="category terms"),
        ],
        reasoning="Split brand and non-brand.",
    )


def _keywords() -> KeywordPlanOutput:
    return KeywordPlanOutput(
        groups=[
            AdGroupKeywords(
                ad_group_name="Brand",
                keywords=[
                    KeywordSpec(
                        text="acme crm",
                        match_type=MatchType.PHRASE,
                        intent=KeywordIntent.TRANSACTIONAL,
                    )
                ],
                negative_keywords=["free"],
            ),
            AdGroupKeywords(
                ad_group_name="CRM Software",
                keywords=[
                    KeywordSpec(
                        text="best crm software",
                        match_type=MatchType.PHRASE,
                        intent=KeywordIntent.COMMERCIAL,
                    )
                ],
                negative_keywords=[],
            ),
        ],
        shared_negative_keywords=["jobs"],
        reasoning="Intent-grouped keywords.",
    )


def _ad_creative() -> AdCreativeOutput:
    return AdCreativeOutput(
        ads=[
            RSACreative(
                ad_group_name="Brand",
                headlines=_HEADLINES,
                descriptions=_DESCRIPTIONS,
                final_url="https://acme.example.com",
            ),
            RSACreative(
                ad_group_name="CRM Software",
                headlines=_HEADLINES,
                descriptions=_DESCRIPTIONS,
                final_url="https://acme.example.com",
            ),
        ],
        extensions=AdExtensions(
            sitelinks=[Sitelink(text="Pricing", url="https://acme.example.com/pricing")],
            callouts=["Free trial", "24/7 support"],
        ),
        reasoning="Benefit-led copy.",
    )


def _website_analysis() -> WebsiteAnalysisOutput:
    return WebsiteAnalysisOutput(
        business_summary="Acme CRM helps SMB sales teams.",
        products=["Acme CRM Pro"],
        services=["Onboarding"],
        target_customer="SMB sales managers",
        keywords=["crm", "sales pipeline"],
        selling_points=["Easy to use"],
        competitors=["OtherCRM"],
        recommended_strategy="Search campaign on high-intent terms.",
        reasoning="Derived from homepage content.",
    )


class _FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self._registry = {
            "WebsiteAnalysisOutput": _website_analysis(),
            "CampaignStrategyPlan": _strategy(),
            "KeywordPlanOutput": _keywords(),
            "AdCreativeOutput": _ad_creative(),
        }

    async def complete_structured(self, *, system, user, schema, temperature=0.4):
        return StructuredResult(
            data=self._registry[schema.__name__], raw="{}", usage=Usage(60, 40, 100)
        )


class _FakeAdsWrapper:
    def __init__(self, fail: bool = False, **_: object) -> None:
        self.fail = fail

    def build_full_campaign(self, *, customer_id, structure, paused=True):
        return {
            "campaign_id": "555",
            "campaign_resource_name": f"customers/{customer_id}/campaigns/555",
            "budget_resource_name": f"customers/{customer_id}/campaignBudgets/777",
            "steps": [
                {
                    "action": "create_budget",
                    "resource_type": "campaign_budget",
                    "google_resource_id": "777",
                    "status": "success",
                },
                {
                    "action": "create_campaign",
                    "resource_type": "campaign",
                    "google_resource_id": "555",
                    "status": "success",
                },
                {
                    "action": "create_ad_group",
                    "resource_type": "ad_group",
                    "google_resource_id": "ag1",
                    "status": "success",
                },
                {
                    "action": "add_keywords",
                    "resource_type": "ad_group_criterion",
                    "google_resource_id": "1 keywords",
                    "status": "success",
                },
                {
                    "action": "create_ad",
                    "resource_type": "ad_group_ad",
                    "google_resource_id": "ad1",
                    "status": "success",
                },
            ],
        }


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


ONBOARD = {
    "business_name": "Acme CRM",
    "description": "A CRM for small sales teams.",
    "industry": "SaaS",
    "goal": "generate_leads",
    "budget": {"daily_budget": 20, "monthly_budget": 600, "currency": "USD", "max_cpa": 30},
    "audience": {
        "age_min": 25,
        "age_max": 55,
        "gender": "all",
        "locations": ["US"],
        "interests": ["sales"],
        "pain_points": ["manual tracking"],
    },
    "products": [
        {
            "name": "Acme CRM Pro",
            "pricing": "$29/mo",
            "features": ["pipeline"],
            "benefits": ["save time"],
            "landing_url": "https://acme.example.com",
        }
    ],
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


async def _seed_connection(db_engine: AsyncEngine, org_id: str) -> None:
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


# ==========================================================================
# Unit: blueprint assembler
# ==========================================================================
def test_assembler_validates_and_merges() -> None:
    strategy = _strategy()
    ads = _ad_creative()
    # Inject an over-long headline that must be dropped.
    ads.ads[0].headlines = ["x" * 40, *_HEADLINES]
    structure = assemble_blueprint(
        strategy=strategy, keywords=_keywords(), ad_creative=ads, daily_budget=20.0
    )
    assert structure.daily_budget == 20.0
    assert len(structure.ad_groups) == 2
    brand = structure.ad_groups[0]
    assert all(len(h) <= 30 for h in brand.ad.headlines)
    assert len(brand.ad.headlines) == 15  # over-long dropped, still 15 valid
    assert brand.keywords[0].text == "acme crm"


def test_assembler_flags_missing_ad_group() -> None:
    strategy = _strategy()
    strategy.ad_groups.append(AdGroupPlan(name="Orphan", theme="no data"))
    structure = assemble_blueprint(
        strategy=strategy, keywords=_keywords(), ad_creative=_ad_creative(), daily_budget=10.0
    )
    assert any("Orphan" in w for w in structure.validation_warnings)


# ==========================================================================
# Onboarding
# ==========================================================================
async def test_save_and_get_onboarding(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/onboarding", headers=headers, json=ONBOARD
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["business_name"] == "Acme CRM"
    assert body["budget"]["daily_budget"] == 20.0
    assert body["products"][0]["name"] == "Acme CRM Pro"

    got = await client.get(f"{API}/organizations/{org_id}/campaigns/onboarding", headers=headers)
    assert got.status_code == 200
    assert got.json()["goal"] == "generate_leads"


async def test_plan_requires_onboarding(client: AsyncClient, fake_llm: None) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/plan",
        headers=headers,
        json={"analyze_website": False},
    )
    assert resp.status_code == 404


# ==========================================================================
# Planning workflow
# ==========================================================================
async def test_plan_workflow_builds_blueprint(client: AsyncClient, fake_llm: None) -> None:
    headers, org_id = await _register_owner(client)
    await client.post(
        f"{API}/organizations/{org_id}/campaigns/onboarding", headers=headers, json=ONBOARD
    )
    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/plan",
        headers=headers,
        json={"analyze_website": False},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # Decision log: strategy -> keywords -> ad copy
    assert [s["agent_name"] for s in body["run"]["steps"]] == [
        "strategy_architect",
        "keyword_planner",
        "ad_creative",
    ]

    bp = body["blueprint"]
    assert bp["status"] == "draft"
    assert bp["campaign_type"] == "SEARCH"
    # Budget clamped to the user's daily budget (20), below AI's 50 recommendation.
    assert bp["daily_budget"] == 20.0
    assert len(bp["structure"]["ad_groups"]) == 2
    assert bp["structure"]["ad_groups"][0]["ad"]["headlines"]


async def test_plan_with_website_analysis(
    client: AsyncClient, fake_llm: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_fetch(url: str, **_: object) -> WebsiteContent:
        return WebsiteContent(url=url, title="Acme", description="CRM", text="Acme CRM homepage.")

    monkeypatch.setattr("app.services.campaign_creation.fetch_website_content", _fake_fetch)
    headers, org_id = await _register_owner(client)
    payload = {**ONBOARD, "website_url": "https://acme.example.com"}
    await client.post(
        f"{API}/organizations/{org_id}/campaigns/onboarding", headers=headers, json=payload
    )
    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/plan",
        headers=headers,
        json={"analyze_website": True},
    )
    assert resp.status_code == 201, resp.text
    names = [s["agent_name"] for s in resp.json()["run"]["steps"]]
    assert names[0] == "website_analysis"
    assert names == ["website_analysis", "strategy_architect", "keyword_planner", "ad_creative"]


# ==========================================================================
# Execution + safety
# ==========================================================================
async def _plan(client: AsyncClient, headers: dict, org_id: str) -> str:
    await client.post(
        f"{API}/organizations/{org_id}/campaigns/onboarding", headers=headers, json=ONBOARD
    )
    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/plan",
        headers=headers,
        json={"analyze_website": False},
    )
    return resp.json()["blueprint"]["id"]


async def test_execute_creates_campaign_and_logs(
    client: AsyncClient, db_engine: AsyncEngine, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)
    blueprint_id = await _plan(client, headers, org_id)

    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/{blueprint_id}/execute",
        headers=headers,
        json={"customer_id": CUSTOMER_ID, "start_paused": True},
    )
    assert resp.status_code == 201, resp.text
    bp = resp.json()
    assert bp["status"] == "created"
    assert bp["google_campaign_id"] == "555"

    logs = await client.get(
        f"{API}/organizations/{org_id}/campaigns/{blueprint_id}/execution-logs", headers=headers
    )
    assert logs.status_code == 200
    actions = [log["action"] for log in logs.json()]
    assert "create_campaign" in actions and "create_ad" in actions


async def test_execute_duplicate_blueprint_conflict(
    client: AsyncClient, db_engine: AsyncEngine, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)
    blueprint_id = await _plan(client, headers, org_id)

    first = await client.post(
        f"{API}/organizations/{org_id}/campaigns/{blueprint_id}/execute",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert first.status_code == 201
    second = await client.post(
        f"{API}/organizations/{org_id}/campaigns/{blueprint_id}/execute",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert second.status_code == 409


async def test_execute_requires_connection(
    client: AsyncClient, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    blueprint_id = await _plan(client, headers, org_id)
    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/{blueprint_id}/execute",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert resp.status_code == 404  # no Google Ads connection


async def test_execute_budget_safety_cap(
    client: AsyncClient, db_engine: AsyncEngine, fake_llm: None, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)

    # Seed a blueprint whose daily budget exceeds the safety cap.
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        bp = CampaignBlueprint(
            organization_id=uuid.UUID(org_id),
            campaign_name="Oversized",
            campaign_type="SEARCH",
            objective="Leads",
            daily_budget=5000,
            bidding_strategy="MANUAL_CPC",
            structure={"campaign_name": "Oversized", "ad_groups": []},
            status="draft",
        )
        session.add(bp)
        await session.commit()
        blueprint_id = str(bp.id)

    resp = await client.post(
        f"{API}/organizations/{org_id}/campaigns/{blueprint_id}/execute",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert resp.status_code == 422  # budget exceeds safety cap
