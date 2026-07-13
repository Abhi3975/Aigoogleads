"""Run context shared by all agents within a supervised workflow.

Responsible for decision logging (persisting each agent step with its reasoning
and token usage) and durable memory access.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm.base import LLMProvider, Usage
from app.models.agent import AgentRun
from app.repositories.agent import AgentMemoryRepository, AgentStepRepository


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


class RunContext:
    def __init__(
        self,
        *,
        session: AsyncSession,
        run: AgentRun,
        provider: LLMProvider,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> None:
        self.session = session
        self.run = run
        self.provider = provider
        self.organization_id = organization_id
        self.actor_user_id = actor_user_id
        self._steps = AgentStepRepository(session)
        self._memory = AgentMemoryRepository(session)
        self._sequence = 0
        self.total_tokens = 0

    # -- Decision logging --------------------------------------------------
    async def log_step(
        self,
        *,
        agent_name: str,
        input: Any,
        output: Any = None,
        reasoning: str | None = None,
        tool_calls: list[Any] | None = None,
        usage: Usage | None = None,
        status: str = "completed",
    ) -> None:
        self._sequence += 1
        if usage is not None:
            self.total_tokens += usage.total_tokens
        await self._steps.create(
            run_id=self.run.id,
            sequence=self._sequence,
            agent_name=agent_name,
            status=status,
            input=_to_jsonable(input) or {},
            output=_to_jsonable(output),
            reasoning=reasoning,
            tool_calls=tool_calls or [],
            usage=usage.as_dict() if usage else {},
        )
        await self.session.flush()

    # -- Memory ------------------------------------------------------------
    async def remember(self, namespace: str, key: str, value: dict[str, Any]) -> None:
        await self._memory.upsert(
            organization_id=self.organization_id, namespace=namespace, key=key, value=value
        )
        await self.session.flush()

    async def recall(self, namespace: str, key: str) -> dict[str, Any] | None:
        entry = await self._memory.get_entry(self.organization_id, namespace, key)
        return entry.value if entry is not None else None
