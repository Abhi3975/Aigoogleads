"""AI orchestration service — creates runs, drives the supervisor, persists results."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import RunContext
from app.agents.llm.provider import get_provider
from app.agents.supervisor import SupervisorAgent
from app.agents.tools import GoogleAdsToolset
from app.core.context import RequestMeta
from app.core.logging import get_logger
from app.models.agent import AgentRun
from app.repositories.agent import AgentMemoryRepository, AgentRunRepository
from app.schemas.agents import BusinessContext
from app.services.google_ads import GoogleAdsService

logger = get_logger(__name__)


class AIService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = AgentRunRepository(session)
        self.memory = AgentMemoryRepository(session)
        self.ads = GoogleAdsService(session)

    async def _start_run(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        workflow: str,
        input_payload: dict,
    ) -> AgentRun:
        run = await self.runs.create(
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            workflow=workflow,
            status="running",
            input=input_payload,
            started_at=datetime.now(UTC),
        )
        await self.session.commit()
        return run

    async def _finish_ok(self, run: AgentRun, ctx: RunContext, output: dict) -> None:
        run.output = output
        run.status = "completed"
        run.total_tokens = ctx.total_tokens
        run.completed_at = datetime.now(UTC)
        await self.session.commit()

    async def _finish_error(self, run: AgentRun, error: str) -> None:
        run.status = "failed"
        run.error = error
        run.completed_at = datetime.now(UTC)
        await self.session.commit()

    async def run_campaign_plan(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        business: BusinessContext,
    ) -> AgentRun:
        provider = get_provider()
        run = await self._start_run(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            workflow="campaign_plan",
            input_payload=business.model_dump(mode="json"),
        )
        ctx = RunContext(
            session=self.session,
            run=run,
            provider=provider,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        try:
            plan = await SupervisorAgent(ctx).plan_campaigns(business)
            await self._finish_ok(run, ctx, plan.model_dump(mode="json"))
        except Exception as exc:
            logger.warning("campaign_plan_failed", error=str(exc))
            await self._finish_error(run, str(exc))
            raise
        return await self._reload(run.id, organization_id)

    async def run_optimization(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        customer_id: str,
        date_range: str = "LAST_30_DAYS",
        auto_execute: bool = False,
        meta: RequestMeta | None = None,
    ) -> AgentRun:
        provider = get_provider()
        # Fail fast if there is no active connection for this org.
        await self.ads.require_connection(organization_id)

        run = await self._start_run(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            workflow="optimization",
            input_payload={
                "customer_id": customer_id,
                "date_range": date_range,
                "auto_execute": auto_execute,
            },
        )
        ctx = RunContext(
            session=self.session,
            run=run,
            provider=provider,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        toolset = GoogleAdsToolset(
            service=self.ads,
            organization_id=organization_id,
            customer_id=customer_id,
            actor_user_id=actor_user_id,
            meta=meta,
        )
        try:
            result = await SupervisorAgent(ctx).optimize(
                toolset, date_range=date_range, auto_execute=auto_execute
            )
            await self._finish_ok(run, ctx, result.model_dump(mode="json"))
        except Exception as exc:
            logger.warning("optimization_failed", error=str(exc))
            await self._finish_error(run, str(exc))
            raise
        return await self._reload(run.id, organization_id)

    async def _reload(self, run_id: uuid.UUID, organization_id: uuid.UUID) -> AgentRun:
        run = await self.runs.get_with_steps(run_id, organization_id)
        assert run is not None
        return run

    async def list_runs(
        self, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> list[AgentRun]:
        return await self.runs.list_for_org(organization_id, offset=offset, limit=limit)

    async def get_run(self, run_id: uuid.UUID, organization_id: uuid.UUID) -> AgentRun | None:
        return await self.runs.get_with_steps(run_id, organization_id)

    async def list_memory(self, organization_id: uuid.UUID, namespace: str) -> list:
        return await self.memory.list_namespace(organization_id, namespace)
