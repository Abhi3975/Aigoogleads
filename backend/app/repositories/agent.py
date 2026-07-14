"""Repositories for agent runs, steps, and memory."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import AgentMemory, AgentRun, AgentStep, AIInsight
from app.repositories.base import BaseRepository


class AgentRunRepository(BaseRepository[AgentRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AgentRun, session)

    async def list_for_org(
        self, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.organization_id == organization_id)
            .order_by(AgentRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_steps(
        self, run_id: uuid.UUID, organization_id: uuid.UUID
    ) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .where(AgentRun.id == run_id, AgentRun.organization_id == organization_id)
            .options(selectinload(AgentRun.steps))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class AgentStepRepository(BaseRepository[AgentStep]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AgentStep, session)


class AgentMemoryRepository(BaseRepository[AgentMemory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AgentMemory, session)

    async def get_entry(
        self, organization_id: uuid.UUID, namespace: str, key: str
    ) -> AgentMemory | None:
        return await self.get_by(organization_id=organization_id, namespace=namespace, key=key)

    async def upsert(
        self, *, organization_id: uuid.UUID, namespace: str, key: str, value: dict[str, Any]
    ) -> AgentMemory:
        existing = await self.get_entry(organization_id, namespace, key)
        if existing is not None:
            return await self.update(existing, value=value)
        return await self.create(
            organization_id=organization_id, namespace=namespace, key=key, value=value
        )

    async def list_namespace(self, organization_id: uuid.UUID, namespace: str) -> list[AgentMemory]:
        stmt = (
            select(AgentMemory)
            .where(
                AgentMemory.organization_id == organization_id,
                AgentMemory.namespace == namespace,
            )
            .order_by(AgentMemory.key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AIInsightRepository(BaseRepository[AIInsight]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIInsight, session)

    async def list_ranked(
        self,
        organization_id: uuid.UUID,
        *,
        insight_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AIInsight]:
        """Insights ordered by importance, then recency (retrieval ranking)."""
        stmt = select(AIInsight).where(AIInsight.organization_id == organization_id)
        if insight_type is not None:
            stmt = stmt.where(AIInsight.insight_type == insight_type)
        stmt = (
            stmt.order_by(AIInsight.importance_score.desc(), AIInsight.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
