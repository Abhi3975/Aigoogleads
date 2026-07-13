"""Organization & membership repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import Organization, OrganizationMembership
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Organization, session)

    async def get_by_slug(self, slug: str) -> Organization | None:
        return await self.get_by(slug=slug)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        """Organizations the user is a member of (excludes soft-deleted)."""
        stmt = (
            select(Organization)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                OrganizationMembership.user_id == user_id,
                Organization.deleted_at.is_(None),
            )
            .order_by(Organization.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class MembershipRepository(BaseRepository[OrganizationMembership]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OrganizationMembership, session)

    async def get_membership(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMembership | None:
        return await self.get_by(organization_id=organization_id, user_id=user_id)

    async def list_members(self, organization_id: uuid.UUID) -> list[OrganizationMembership]:
        stmt = (
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .options(selectinload(OrganizationMembership.user))
            .order_by(OrganizationMembership.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_user(self, user_id: uuid.UUID) -> list[OrganizationMembership]:
        """Memberships for a user with their organizations eagerly loaded."""
        stmt = (
            select(OrganizationMembership)
            .join(Organization, Organization.id == OrganizationMembership.organization_id)
            .where(
                OrganizationMembership.user_id == user_id,
                Organization.deleted_at.is_(None),
            )
            .options(selectinload(OrganizationMembership.organization))
            .order_by(OrganizationMembership.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
