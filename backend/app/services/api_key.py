"""API key service — issue, list, revoke, and verify keys.

The full secret is returned only once at creation; only a SHA-256 hash and a
display prefix are stored.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sha256
from app.models.api_key import APIKey
from app.repositories.api_key import APIKeyRepository

_KEY_PREFIX = "aia_"


class APIKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = APIKeyRepository(session)

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        actor_user_id: uuid.UUID | None = None,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[APIKey, str]:
        raw = _KEY_PREFIX + secrets.token_urlsafe(32)
        key = await self.repo.create(
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            name=name,
            prefix=raw[:12],
            key_hash=sha256(raw),
            scopes=scopes or [],
            expires_at=expires_at,
        )
        await self.session.commit()
        await self.session.refresh(key)
        return key, raw

    async def list(self, organization_id: uuid.UUID) -> list[APIKey]:
        return await self.repo.list_for_org(organization_id)

    async def revoke(self, organization_id: uuid.UUID, key_id: uuid.UUID) -> bool:
        key = await self.repo.get_for_org(key_id, organization_id)
        if key is None:
            return False
        if key.revoked_at is None:
            key.revoked_at = datetime.now(UTC)
            await self.session.commit()
        return True

    async def verify(self, raw_key: str | None) -> APIKey | None:
        if not raw_key:
            return None
        key = await self.repo.get_active_by_hash(sha256(raw_key))
        if key is None:
            return None
        key.last_used_at = datetime.now(UTC)
        await self.session.commit()
        return key
