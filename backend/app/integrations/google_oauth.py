"""Google OAuth 2.0 client for passwordless sign-in.

Implements the authorization-code flow against Google's public endpoints:
build authorization URL -> exchange code for tokens -> fetch OpenID userinfo.
The Google Ads-specific scopes and token storage are added in Milestone 4.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

# Minimal scopes for authentication only.
LOGIN_SCOPES = ("openid", "email", "profile")


class GoogleOAuthClient:
    def __init__(self) -> None:
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def build_authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(LOGIN_SCOPES),
            "state": state,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
        return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(TOKEN_ENDPOINT, data=data)
        if resp.status_code != 200:
            raise ExternalServiceError(
                "Failed to exchange Google authorization code.",
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        return resp.json()

    async def fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            raise ExternalServiceError(
                "Failed to fetch Google user profile.",
                details={"status": resp.status_code},
            )
        return resp.json()
