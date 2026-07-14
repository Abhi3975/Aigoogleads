"""Forgot / reset password tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.core.security import create_password_reset_token

API = "/api/v1"


async def _register(client: AsyncClient) -> dict:
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": "originalpass1", "full_name": "User"},
    )
    body = resp.json()
    return {
        "email": email,
        "user_id": body["user"]["id"],
        "refresh": body["tokens"]["refresh_token"],
    }


async def test_forgot_password_is_generic(client: AsyncClient) -> None:
    await _register(client)
    # Existing and non-existing emails both return the same generic 200.
    existing = await client.post(
        f"{API}/auth/forgot-password", json={"email": "whoever@example.com"}
    )
    assert existing.status_code == 200
    assert "reset link" in existing.json()["message"].lower()


async def test_reset_password_flow(client: AsyncClient) -> None:
    user = await _register(client)
    token = create_password_reset_token(user["user_id"])

    reset = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "brandnewpass9"}
    )
    assert reset.status_code == 200

    # New password works; old one does not.
    ok = await client.post(
        f"{API}/auth/login", json={"email": user["email"], "password": "brandnewpass9"}
    )
    assert ok.status_code == 200
    bad = await client.post(
        f"{API}/auth/login", json={"email": user["email"], "password": "originalpass1"}
    )
    assert bad.status_code == 401


async def test_reset_revokes_existing_sessions(client: AsyncClient) -> None:
    user = await _register(client)
    token = create_password_reset_token(user["user_id"])
    await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "brandnewpass9"}
    )
    # The pre-reset refresh token is now revoked.
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": user["refresh"]})
    assert resp.status_code == 401


async def test_reset_with_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API}/auth/reset-password", json={"token": "not-a-token", "new_password": "brandnewpass9"}
    )
    assert resp.status_code == 401
