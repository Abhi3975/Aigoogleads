"""Optimization policy & log repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.optimization import OptimizationLog, OptimizationPolicy
from app.repositories.base import BaseRepository


class OptimizationPolicyRepository(BaseRepository[OptimizationPolicy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OptimizationPolicy, session)

    async def get_for_org(self, organization_id: uuid.UUID) -> OptimizationPolicy | None:
        return await self.get_by(organization_id=organization_id)

    async def get_or_create(self, organization_id: uuid.UUID) -> OptimizationPolicy:
        existing = await self.get_for_org(organization_id)
        if existing is not None:
            return existing
        policy = await self.create(organization_id=organization_id)
        await self.session.commit()
        return policy


class OptimizationLogRepository(BaseRepository[OptimizationLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OptimizationLog, session)

    async def list_for_org(
        self, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[OptimizationLog]:
        stmt = (
            select(OptimizationLog)
            .where(OptimizationLog.organization_id == organization_id)
            .order_by(OptimizationLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_run(self, run_id: uuid.UUID) -> list[OptimizationLog]:
        stmt = (
            select(OptimizationLog)
            .where(OptimizationLog.run_id == run_id)
            .order_by(OptimizationLog.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())
