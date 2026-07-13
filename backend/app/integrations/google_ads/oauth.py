"""Google Ads OAuth 2.0 (authorization-code) flow.

Requests the ``adwords`` scope with offline access so Google returns a refresh
token, which is encrypted and stored for autonomous API access.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.integrations.google_oauth import AUTHORIZATION_ENDPOINT, TOKEN_ENDPOINT

ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


class GoogleAdsOAuthClient:
    def __init__(self) -> None:
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_ADS_OAUTH_REDIRECT_URI

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and settings.GOOGLE_ADS_DEVELOPER_TOKEN)

    def build_authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": ADS_SCOPE,
            "state": state,
            "access_type": "offline",
            "include_granted_scopes": "true",
            # Force a consent screen so a refresh token is always returned.
            "prompt": "consent",
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
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(TOKEN_ENDPOINT, data=data)
        if resp.status_code != 200:
            raise ExternalServiceError(
                "Failed to exchange Google Ads authorization code.",
                details={"status": resp.status_code, "body": resp.text[:500]},
            )
        return resp.json()
