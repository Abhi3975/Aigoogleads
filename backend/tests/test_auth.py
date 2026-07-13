"""Authentication & RBAC integration tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

API = "/api/v1"


def _email() -> str:
    return f"user_{uuid.uuid4().hex[:12]}@example.com"


async def _register(client: AsyncClient, *, password: str = "supersecret1", full_name: str = "T"):
    email = _email()
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return email, resp


# --------------------------------------------------------------------------
# Registration & login
# --------------------------------------------------------------------------
async def test_register_returns_user_and_tokens(client: AsyncClient) -> None:
    email, resp = await _register(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == email
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["tokens"]["token_type"] == "bearer"


async def test_register_duplicate_conflict(client: AsyncClient) -> None:
    email, first = await _register(client)
    assert first.status_code == 201
    dup = await client.post(
        f"{API}/auth/register", json={"email": email, "password": "supersecret1"}
    )
    assert dup.status_code == 409


async def test_login_success(client: AsyncClient) -> None:
    email, reg = await _register(client, password="supersecret1")
    assert reg.status_code == 201
    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": "supersecret1"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


async def test_login_wrong_password(client: AsyncClient) -> None:
    email, _ = await _register(client, password="supersecret1")
    resp = await client.post(
        f"{API}/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API}/auth/login", json={"email": _email(), "password": "supersecret1"}
    )
    assert resp.status_code == 401


# --------------------------------------------------------------------------
# Current user / auth guard
# --------------------------------------------------------------------------
async def test_me_with_token(client: AsyncClient) -> None:
    email, reg = await _register(client)
    access = reg.json()["tokens"]["access_token"]
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/auth/me")
    assert resp.status_code == 401


async def test_me_rejects_garbage_token(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


# --------------------------------------------------------------------------
# Refresh rotation & reuse detection
# --------------------------------------------------------------------------
async def test_refresh_rotates_token(client: AsyncClient) -> None:
    _, reg = await _register(client)
    refresh = reg.json()["tokens"]["refresh_token"]
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200, resp.text
    assert resp.json()["refresh_token"] != refresh


async def test_refresh_reuse_detection_revokes_family(client: AsyncClient) -> None:
    _, reg = await _register(client)
    original = reg.json()["tokens"]["refresh_token"]

    rotated = await client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]

    # Replaying the original (now revoked) token is treated as theft.
    replay = await client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert replay.status_code == 401

    # The whole family is revoked, so even the freshly rotated token is dead.
    after = await client.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    _, reg = await _register(client)
    refresh = reg.json()["tokens"]["refresh_token"]
    logout = await client.post(f"{API}/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 204
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


# --------------------------------------------------------------------------
# Organizations & RBAC
# --------------------------------------------------------------------------
async def test_default_workspace_created_on_register(client: AsyncClient) -> None:
    _, reg = await _register(client, full_name="Owner")
    access = reg.json()["tokens"]["access_token"]
    resp = await client.get(f"{API}/organizations", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    orgs = resp.json()
    assert len(orgs) == 1
    assert orgs[0]["role"] == "owner"


async def test_rbac_add_member_and_permission_enforced(client: AsyncClient) -> None:
    # Owner
    _, owner_reg = await _register(client, full_name="Owner")
    owner_token = owner_reg.json()["tokens"]["access_token"]
    owner_h = {"Authorization": f"Bearer {owner_token}"}
    org_id = (await client.get(f"{API}/organizations", headers=owner_h)).json()[0]["id"]

    # Second user
    member_email, member_reg = await _register(client, full_name="Member")
    member_token = member_reg.json()["tokens"]["access_token"]
    member_h = {"Authorization": f"Bearer {member_token}"}

    # Owner adds the second user as analyst
    add = await client.post(
        f"{API}/organizations/{org_id}/members",
        headers=owner_h,
        json={"email": member_email, "role": "analyst"},
    )
    assert add.status_code == 201, add.text
    assert add.json()["role"] == "analyst"

    # Now two members
    members = await client.get(f"{API}/organizations/{org_id}/members", headers=owner_h)
    assert members.status_code == 200
    assert len(members.json()) == 2

    # Analyst cannot add members (needs admin+)
    forbidden = await client.post(
        f"{API}/organizations/{org_id}/members",
        headers=member_h,
        json={"email": _email(), "role": "viewer"},
    )
    assert forbidden.status_code == 403

    # Non-member cannot view members
    _, outsider_reg = await _register(client)
    outsider_h = {"Authorization": f"Bearer {outsider_reg.json()['tokens']['access_token']}"}
    denied = await client.get(f"{API}/organizations/{org_id}/members", headers=outsider_h)
    assert denied.status_code == 403
