"""Performance report tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.security import encrypt_secret
from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection

API = "/api/v1"
CUSTOMER_ID = "1234567890"


class _FakeAdsWrapper:
    def __init__(self, **_: object) -> None:
        pass

    def search(self, customer_id: str, query: str) -> list[object]:
        # Reports only fetch metrics.
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
            refresh_token_encrypted=encrypt_secret("fake"),
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


async def test_generate_and_list_report(
    client: AsyncClient, db_engine: AsyncEngine, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)

    gen = await client.post(
        f"{API}/organizations/{org_id}/reports/generate",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["totals"]["cost"] == 25.0
    assert body["totals"]["roas"] == 8.0
    assert "campaigns" in body["summary"]

    listing = await client.get(f"{API}/organizations/{org_id}/reports", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_generate_is_idempotent_per_day(
    client: AsyncClient, db_engine: AsyncEngine, fake_ads: None
) -> None:
    headers, org_id = await _register_owner(client)
    await _seed(db_engine, org_id)
    for _ in range(2):
        resp = await client.post(
            f"{API}/organizations/{org_id}/reports/generate",
            headers=headers,
            json={"customer_id": CUSTOMER_ID},
        )
        assert resp.status_code == 201
    listing = await client.get(f"{API}/organizations/{org_id}/reports", headers=headers)
    assert len(listing.json()) == 1  # upserted, not duplicated


async def test_generate_requires_connection(client: AsyncClient, fake_ads: None) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/reports/generate",
        headers=headers,
        json={"customer_id": CUSTOMER_ID},
    )
    assert resp.status_code == 404
