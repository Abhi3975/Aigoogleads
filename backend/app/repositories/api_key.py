"""API key repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.repositories.base import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(APIKey, session)

    async def list_for_org(self, organization_id: uuid.UUID) -> list[APIKey]:
        stmt = (
            select(APIKey)
            .where(APIKey.organization_id == organization_id)
            .order_by(APIKey.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_org(self, key_id: uuid.UUID, organization_id: uuid.UUID) -> APIKey | None:
        return await self.get_by(id=key_id, organization_id=organization_id)

    async def get_active_by_hash(self, key_hash: str) -> APIKey | None:
        stmt = select(APIKey).where(APIKey.key_hash == key_hash, APIKey.revoked_at.is_(None))
        key = (await self.session.execute(stmt)).scalars().first()
        if key is None:
            return None
        if key.expires_at is not None and key.expires_at < datetime.now(UTC):
            return None
        return key
