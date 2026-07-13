"""Google Ads integration tests.

The google-ads SDK is not exercised live (that requires real credentials and a
test account). Instead we verify every unit we own end-to-end: OAuth URL/state,
token encryption, GAQL builders, row->schema mappers, and the full service +
endpoint flow with an injected fake client.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.exceptions import ValidationError
from app.core.security import (
    create_signed_state,
    decrypt_secret,
    encrypt_secret,
    verify_signed_state,
)
from app.integrations.google_ads.mappers import map_campaign, map_customer, map_metrics
from app.integrations.google_ads.oauth import ADS_SCOPE, GoogleAdsOAuthClient
from app.integrations.google_ads.queries import campaign_metrics_query, validate_date_range
from app.models.google_ads import GoogleAdsConnection

API = "/api/v1"


# ==========================================================================
# Unit tests (no HTTP, no DB)
# ==========================================================================
def test_encryption_round_trip() -> None:
    secret = "1//0abcDEFrefresh-token-value"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_signed_state_round_trip() -> None:
    token = create_signed_state({"org": "abc", "nonce": "xyz"})
    payload = verify_signed_state(token)
    assert payload["org"] == "abc"
    assert payload["nonce"] == "xyz"
    assert payload["purpose"] == "oauth_state"


def test_validate_date_range() -> None:
    assert validate_date_range("last_30_days") == "LAST_30_DAYS"
    with pytest.raises(ValidationError):
        validate_date_range("DROP TABLE campaigns")


def test_metrics_query_contains_validated_range() -> None:
    q = campaign_metrics_query("LAST_7_DAYS")
    assert "DURING LAST_7_DAYS" in q
    assert "metrics.impressions" in q


def test_oauth_authorization_url() -> None:
    url = GoogleAdsOAuthClient().build_authorization_url(state="the-state")
    assert ADS_SCOPE in url.replace("%3A", ":").replace("%2F", "/")
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=the-state" in url


def test_map_campaign() -> None:
    row = SimpleNamespace(
        campaign=SimpleNamespace(
            id=111,
            name="Brand",
            status="ENABLED",
            advertising_channel_type="SEARCH",
            bidding_strategy_type="MANUAL_CPC",
        ),
        campaign_budget=SimpleNamespace(amount_micros=10_000_000),
    )
    out = map_campaign(row)
    assert out.id == "111"
    assert out.name == "Brand"
    assert out.status == "ENABLED"
    assert out.channel_type == "SEARCH"
    assert out.daily_budget == 10.0


def test_map_metrics_computes_derived_values() -> None:
    row = SimpleNamespace(
        campaign=SimpleNamespace(id=111, name="Brand"),
        metrics=SimpleNamespace(
            impressions=1000,
            clicks=50,
            cost_micros=25_000_000,  # $25
            conversions=5,
            conversions_value=200.0,
            ctr=0.05,
            average_cpc=500_000,  # $0.50
        ),
    )
    out = map_metrics(row)
    assert out.cost == 25.0
    assert out.average_cpc == 0.5
    assert out.cost_per_conversion == 5.0  # 25 / 5
    assert out.roas == 8.0  # 200 / 25


def test_map_customer() -> None:
    row = SimpleNamespace(
        customer=SimpleNamespace(
            id=1234567890,
            descriptive_name="Test Account",
            currency_code="USD",
            time_zone="America/New_York",
            manager=False,
            test_account=True,
        )
    )
    info = map_customer(row)
    assert info["customer_id"] == "1234567890"
    assert info["is_test_account"] is True


# ==========================================================================
# Endpoint integration tests (fake Google Ads client)
# ==========================================================================
class _FakeWrapper:
    """Duck-typed stand-in for GoogleAdsClientWrapper."""

    def __init__(self, **_: object) -> None:
        pass

    def list_accessible_customers(self) -> list[str]:
        return ["1234567890"]

    def get_customer(self, customer_id: str) -> object:
        return SimpleNamespace(
            customer=SimpleNamespace(
                id=int(customer_id),
                descriptive_name="Test Account",
                currency_code="USD",
                time_zone="America/New_York",
                manager=False,
                test_account=True,
            )
        )

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

    def create_campaign(
        self, *, customer_id: str, name: str, daily_budget: float, paused: bool
    ) -> dict[str, str]:
        return {
            "campaign_id": "222",
            "campaign_resource_name": f"customers/{customer_id}/campaigns/222",
            "budget_resource_name": f"customers/{customer_id}/campaignBudgets/333",
            "status": "PAUSED" if paused else "ENABLED",
        }


@pytest.fixture
def fake_ads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.integrations.google_ads.client.create_wrapper",
        lambda **kwargs: _FakeWrapper(**kwargs),
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


async def _seed_connection(db_engine: AsyncEngine, org_id: str) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            GoogleAdsConnection(
                organization_id=uuid.UUID(org_id),
                refresh_token_encrypted=encrypt_secret("fake-refresh-token"),
                scopes=ADS_SCOPE,
                status="active",
            )
        )
        await session.commit()


async def test_connect_requires_configuration(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    # Server has no Google Ads credentials configured in the test env.
    resp = await client.post(f"{API}/organizations/{org_id}/google-ads/connect", headers=headers)
    assert resp.status_code == 422


async def test_sync_and_list_accounts(
    client: AsyncClient, db_engine: AsyncEngine, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)

    synced = await client.post(
        f"{API}/organizations/{org_id}/google-ads/accounts/sync", headers=headers
    )
    assert synced.status_code == 200, synced.text
    accounts = synced.json()
    assert len(accounts) == 1
    assert accounts[0]["customer_id"] == "1234567890"
    assert accounts[0]["is_test_account"] is True

    listed = await client.get(f"{API}/organizations/{org_id}/google-ads/accounts", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_read_campaigns(client: AsyncClient, db_engine: AsyncEngine, fake_ads: None) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)
    await client.post(f"{API}/organizations/{org_id}/google-ads/accounts/sync", headers=headers)

    resp = await client.get(
        f"{API}/organizations/{org_id}/google-ads/accounts/1234567890/campaigns",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    campaigns = resp.json()
    assert len(campaigns) == 1
    assert campaigns[0]["daily_budget"] == 10.0
    assert campaigns[0]["status"] == "ENABLED"


async def test_read_metrics(client: AsyncClient, db_engine: AsyncEngine, fake_ads: None) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)
    await client.post(f"{API}/organizations/{org_id}/google-ads/accounts/sync", headers=headers)

    resp = await client.get(
        f"{API}/organizations/{org_id}/google-ads/accounts/1234567890/campaigns/metrics",
        params={"date_range": "LAST_30_DAYS"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    metrics = resp.json()[0]
    assert metrics["roas"] == 8.0
    assert metrics["cost_per_conversion"] == 5.0


async def test_metrics_rejects_bad_date_range(
    client: AsyncClient, db_engine: AsyncEngine, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)
    await client.post(f"{API}/organizations/{org_id}/google-ads/accounts/sync", headers=headers)

    resp = await client.get(
        f"{API}/organizations/{org_id}/google-ads/accounts/1234567890/campaigns/metrics",
        params={"date_range": "'; DROP TABLE campaigns; --"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_create_test_campaign(
    client: AsyncClient, db_engine: AsyncEngine, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed_connection(db_engine, org_id)
    await client.post(f"{API}/organizations/{org_id}/google-ads/accounts/sync", headers=headers)

    resp = await client.post(
        f"{API}/organizations/{org_id}/google-ads/accounts/1234567890/campaigns",
        headers=headers,
        json={"name": "Test Campaign", "daily_budget": 20.0},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["campaign_id"] == "222"
    assert body["status"] == "PAUSED"


async def test_campaigns_require_connection(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.get(
        f"{API}/organizations/{org_id}/google-ads/accounts/1234567890/campaigns",
        headers=headers,
    )
    assert resp.status_code == 404
