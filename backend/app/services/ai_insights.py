"""AI insight / learning-memory service.

Agents record durable observations (learnings) with an importance score; the
platform retrieves them ranked by importance so the most useful knowledge is
surfaced first — the substrate of self-improvement over time.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AIInsight
from app.repositories.agent import AIInsightRepository


class AIInsightService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AIInsightRepository(session)

    async def record(
        self,
        *,
        organization_id: uuid.UUID,
        agent_name: str,
        insight_type: str,
        observation: str,
        outcome: str | None = None,
        importance_score: float = 0.5,
        confidence: float = 0.5,
        data: dict[str, Any] | None = None,
    ) -> AIInsight:
        insight = await self.repo.create(
            organization_id=organization_id,
            agent_name=agent_name,
            insight_type=insight_type,
            observation=observation,
            outcome=outcome,
            importance_score=max(0.0, min(1.0, importance_score)),
            confidence=max(0.0, min(1.0, confidence)),
            data=data or {},
        )
        await self.session.flush()
        return insight

    async def list_ranked(
        self,
        organization_id: uuid.UUID,
        *,
        insight_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AIInsight]:
        return await self.repo.list_ranked(
            organization_id, insight_type=insight_type, offset=offset, limit=limit
        )
