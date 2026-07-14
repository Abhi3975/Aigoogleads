"""Repositories for campaign-creation domain models."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import (
    BusinessProfile,
    CampaignBlueprint,
    CampaignExecutionLog,
    WebsiteAnalysis,
)
from app.repositories.base import BaseRepository


class BusinessProfileRepository(BaseRepository[BusinessProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BusinessProfile, session)

    async def get_current(self, organization_id: uuid.UUID) -> BusinessProfile | None:
        """Most recent active profile with budget/audience/products eagerly loaded."""
        stmt = (
            select(BusinessProfile)
            .where(
                BusinessProfile.organization_id == organization_id,
                BusinessProfile.deleted_at.is_(None),
            )
            .options(
                selectinload(BusinessProfile.budget),
                selectinload(BusinessProfile.audience),
                selectinload(BusinessProfile.products),
            )
            .order_by(BusinessProfile.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_children(self, profile_id: uuid.UUID) -> BusinessProfile | None:
        stmt = (
            select(BusinessProfile)
            .where(BusinessProfile.id == profile_id)
            .options(
                selectinload(BusinessProfile.budget),
                selectinload(BusinessProfile.audience),
                selectinload(BusinessProfile.products),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class WebsiteAnalysisRepository(BaseRepository[WebsiteAnalysis]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WebsiteAnalysis, session)


class CampaignBlueprintRepository(BaseRepository[CampaignBlueprint]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CampaignBlueprint, session)

    async def list_for_org(
        self, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CampaignBlueprint]:
        stmt = (
            select(CampaignBlueprint)
            .where(
                CampaignBlueprint.organization_id == organization_id,
                CampaignBlueprint.deleted_at.is_(None),
            )
            .order_by(CampaignBlueprint.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_org(
        self, blueprint_id: uuid.UUID, organization_id: uuid.UUID
    ) -> CampaignBlueprint | None:
        stmt = select(CampaignBlueprint).where(
            CampaignBlueprint.id == blueprint_id,
            CampaignBlueprint.organization_id == organization_id,
            CampaignBlueprint.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def find_created_duplicate(
        self, organization_id: uuid.UUID, customer_id: str, campaign_name: str
    ) -> CampaignBlueprint | None:
        """A blueprint already created in Google Ads with the same name/account."""
        stmt = select(CampaignBlueprint).where(
            CampaignBlueprint.organization_id == organization_id,
            CampaignBlueprint.customer_id == customer_id,
            CampaignBlueprint.campaign_name == campaign_name,
            CampaignBlueprint.status == "created",
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class CampaignExecutionLogRepository(BaseRepository[CampaignExecutionLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CampaignExecutionLog, session)

    async def list_for_blueprint(self, blueprint_id: uuid.UUID) -> list[CampaignExecutionLog]:
        stmt = (
            select(CampaignExecutionLog)
            .where(CampaignExecutionLog.blueprint_id == blueprint_id)
            .order_by(CampaignExecutionLog.sequence)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
