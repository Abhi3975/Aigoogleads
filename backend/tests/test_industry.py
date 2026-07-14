"""Industry template tests."""

from __future__ import annotations

from httpx import AsyncClient

from app.services import industry_templates

API = "/api/v1"


def test_get_template_normalizes_key() -> None:
    assert industry_templates.get_template("SaaS") is not None
    assert industry_templates.get_template("real-estate") is not None
    assert industry_templates.get_template("Local Services") is not None
    assert industry_templates.get_template("nope") is None


async def test_list_industry_templates(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/industry-templates")
    assert resp.status_code == 200
    industries = {t["industry"] for t in resp.json()}
    assert {"ecommerce", "saas", "healthcare"}.issubset(industries)


async def test_get_industry_template(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/industry-templates/ecommerce")
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommended_campaign_type"] == "PERFORMANCE_MAX"
    assert body["keyword_themes"]


async def test_unknown_industry_404(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/industry-templates/spaceships")
    assert resp.status_code == 404
