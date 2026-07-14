"""API key management + key-auth tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

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


async def test_create_key_returns_secret_once(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    resp = await client.post(
        f"{API}/organizations/{org_id}/api-keys",
        headers=headers,
        json={"name": "CI key", "scopes": ["campaigns.read"]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["key"].startswith("aia_")
    assert body["prefix"] == body["key"][:12]

    # Listing never exposes the secret.
    listing = await client.get(f"{API}/organizations/{org_id}/api-keys", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert "key" not in listing.json()[0]


async def test_key_auth_whoami(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    created = await client.post(
        f"{API}/organizations/{org_id}/api-keys", headers=headers, json={"name": "svc"}
    )
    raw = created.json()["key"]

    who = await client.get(f"{API}/api-keys/whoami", headers={"X-API-Key": raw})
    assert who.status_code == 200
    assert who.json()["organization_id"] == org_id
    assert who.json()["name"] == "svc"


async def test_invalid_key_rejected(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/api-keys/whoami", headers={"X-API-Key": "aia_nope"})
    assert resp.status_code == 401
    missing = await client.get(f"{API}/api-keys/whoami")
    assert missing.status_code == 401


async def test_revoked_key_rejected(client: AsyncClient) -> None:
    headers, org_id = await _register_owner(client)
    created = await client.post(
        f"{API}/organizations/{org_id}/api-keys", headers=headers, json={"name": "temp"}
    )
    raw = created.json()["key"]
    key_id = created.json()["id"]

    revoke = await client.delete(f"{API}/organizations/{org_id}/api-keys/{key_id}", headers=headers)
    assert revoke.status_code == 204

    who = await client.get(f"{API}/api-keys/whoami", headers={"X-API-Key": raw})
    assert who.status_code == 401
