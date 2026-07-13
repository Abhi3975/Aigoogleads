"""Google Ads connection & account repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection
from app.repositories.base import BaseRepository


class GoogleAdsConnectionRepository(BaseRepository[GoogleAdsConnection]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GoogleAdsConnection, session)

    async def get_active_for_org(self, organization_id: uuid.UUID) -> GoogleAdsConnection | None:
        stmt = (
            select(GoogleAdsConnection)
            .where(
                GoogleAdsConnection.organization_id == organization_id,
                GoogleAdsConnection.status == "active",
            )
            .order_by(GoogleAdsConnection.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class GoogleAdsAccountRepository(BaseRepository[GoogleAdsAccount]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GoogleAdsAccount, session)

    async def list_for_org(self, organization_id: uuid.UUID) -> list[GoogleAdsAccount]:
        stmt = (
            select(GoogleAdsAccount)
            .where(GoogleAdsAccount.organization_id == organization_id)
            .order_by(GoogleAdsAccount.descriptive_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_customer_id(
        self, organization_id: uuid.UUID, customer_id: str
    ) -> GoogleAdsAccount | None:
        return await self.get_by(organization_id=organization_id, customer_id=customer_id)

    async def upsert(
        self,
        *,
        organization_id: uuid.UUID,
        connection_id: uuid.UUID,
        customer_id: str,
        descriptive_name: str | None,
        currency_code: str | None,
        time_zone: str | None,
        is_manager: bool,
        is_test_account: bool,
    ) -> GoogleAdsAccount:
        existing = await self.get_by_customer_id(organization_id, customer_id)
        values = {
            "connection_id": connection_id,
            "descriptive_name": descriptive_name,
            "currency_code": currency_code,
            "time_zone": time_zone,
            "is_manager": is_manager,
            "is_test_account": is_test_account,
        }
        if existing is not None:
            return await self.update(existing, **values)
        return await self.create(organization_id=organization_id, customer_id=customer_id, **values)
