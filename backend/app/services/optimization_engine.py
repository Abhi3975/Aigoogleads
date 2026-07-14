"""Autonomous optimization engine.

The full loop: fetch metrics -> analyze -> recommend -> safety validation ->
execute (if enabled) -> audit + notify. Reuses the M5 Analytics, Recommendation
and Execution agents/tools; adds the Safety Decision Engine and audit trail.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import RunContext
from app.agents.llm.provider import get_provider
from app.agents.specialists import AnalyticsAgent, RecommendationAgent
from app.agents.tools import GoogleAdsToolset
from app.core.context import RequestMeta
from app.core.logging import get_logger
from app.models.optimization import OptimizationLog
from app.repositories.agent import AgentRunRepository
from app.repositories.optimization import OptimizationLogRepository, OptimizationPolicyRepository
from app.schemas.agents import RecommendationType
from app.services.google_ads import GoogleAdsService
from app.services.metrics import MetricsService, metric_to_payload
from app.services.notification import NotificationService
from app.services.safety import SafetyDecision, SafetyEngine

logger = get_logger(__name__)


class OptimizationEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ads = GoogleAdsService(session)
        self.metrics = MetricsService(session)
        self.policies = OptimizationPolicyRepository(session)
        self.logs = OptimizationLogRepository(session)
        self.runs = AgentRunRepository(session)
        self.notifications = NotificationService(session)

    async def run(
        self,
        *,
        organization_id: uuid.UUID,
        customer_id: str,
        actor_user_id: uuid.UUID | None = None,
        date_range: str | None = None,
        auto_execute: bool | None = None,
        meta: RequestMeta | None = None,
    ) -> dict[str, Any]:
        policy = await self.policies.get_or_create(organization_id)
        dr = date_range or policy.date_range
        do_execute = policy.auto_execute if auto_execute is None else auto_execute
        provider = get_provider()
        await self.ads.require_connection(organization_id)

        run = await self.runs.create(
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            workflow="optimization_loop",
            status="running",
            input={"customer_id": customer_id, "date_range": dr, "auto_execute": do_execute},
            started_at=datetime.now(UTC),
        )
        await self.session.commit()
        ctx = RunContext(
            session=self.session,
            run=run,
            provider=provider,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )

        counts = {"applied": 0, "pending": 0, "rejected": 0, "failed": 0}
        try:
            # 1) Collect metrics + current budgets.
            stored = await self.metrics.fetch_and_store_campaigns(organization_id, customer_id, dr)
            metrics_payload = [metric_to_payload(m) for m in stored]
            campaigns = await self.ads.list_campaigns(organization_id, customer_id)
            budget_by_id = {c.id: float(c.daily_budget or 0) for c in campaigns}
            await ctx.log_step(
                agent_name="metrics_collector",
                input={"date_range": dr, "customer_id": customer_id},
                output={"campaigns": len(campaigns), "metrics": len(stored)},
                reasoning="Fetched and stored Google Ads performance metrics.",
                tool_calls=[{"tool": "get_metrics", "arguments": {"date_range": dr}}],
            )

            # 2) Analyze -> 3) recommend.
            analytics = await AnalyticsAgent().run(ctx, {"metrics": metrics_payload})
            recs = await RecommendationAgent().run(
                ctx, {"analytics": analytics.model_dump(mode="json"), "metrics": metrics_payload}
            )

            # 4) Safety validation.
            context = {
                m.campaign_id: {
                    "budget": budget_by_id.get(m.campaign_id, float(0)),
                    "clicks": m.clicks,
                    "conversions": float(m.conversions),
                    "cost": float(m.cost),
                    "roas": float(m.roas),
                    "days_active": None,
                }
                for m in stored
            }
            decisions = SafetyEngine(policy).evaluate(recs.recommendations, context=context)

            # 5) Execute (if enabled) + audit + notify.
            toolset = GoogleAdsToolset(
                service=self.ads,
                organization_id=organization_id,
                customer_id=customer_id,
                actor_user_id=actor_user_id,
                meta=meta,
            )
            for decision in decisions:
                status = await self._process(
                    decision,
                    do_execute,
                    toolset,
                    context,
                    run.id,
                    organization_id,
                    customer_id,
                    actor_user_id,
                )
                counts[status] = counts.get(status, 0) + 1

            run.output = {"counts": counts, "recommendations": len(recs.recommendations)}
            run.status = "completed"
            run.total_tokens = ctx.total_tokens
            run.completed_at = datetime.now(UTC)
            await self.session.commit()
        except Exception as exc:
            logger.warning("optimization_loop_failed", error=str(exc))
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.now(UTC)
            await self.session.commit()
            raise

        return {"run_id": run.id, "counts": counts}

    async def _process(
        self,
        decision: SafetyDecision,
        do_execute: bool,
        toolset: GoogleAdsToolset,
        context: dict[str, dict[str, Any]],
        run_id: uuid.UUID,
        organization_id: uuid.UUID,
        customer_id: str,
        actor_user_id: uuid.UUID | None,
    ) -> str:
        rec = decision.recommendation
        previous = context.get(rec.target, {}).get("budget")
        new_value = decision.adjusted_value
        api_response: dict[str, Any] = {}

        if not decision.approved:
            status = "rejected"
        elif not do_execute:
            status = "pending"
        else:
            status, api_response = await self._execute(decision, toolset)

        db_status = {
            "rejected": "rejected",
            "pending": "pending",
            "executed": "executed",
            "failed": "failed",
        }[status]
        await self.logs.create(
            organization_id=organization_id,
            run_id=run_id,
            created_by_user_id=actor_user_id,
            customer_id=customer_id,
            campaign_id=rec.target,
            action_type=rec.type.value,
            target=rec.target,
            previous_value=previous if rec.type is RecommendationType.ADJUST_BUDGET else None,
            new_value=new_value,
            reasoning=rec.rationale,
            explanation=decision.explanation,
            confidence=float(rec.confidence),
            status=db_status,
            api_response=api_response,
        )
        await self._notify(organization_id, decision, db_status)
        await self.session.flush()

        return {"executed": "applied"}.get(status, status)

    async def _execute(
        self, decision: SafetyDecision, toolset: GoogleAdsToolset
    ) -> tuple[str, dict[str, Any]]:
        rec = decision.recommendation
        try:
            if rec.type is RecommendationType.ADJUST_BUDGET and decision.adjusted_value is not None:
                result = await toolset.update_budget(
                    campaign_id=rec.target, daily_budget=decision.adjusted_value
                )
            elif rec.type is RecommendationType.PAUSE_CAMPAIGN:
                result = await toolset.pause_campaign(campaign_id=rec.target)
            elif rec.type is RecommendationType.ENABLE_CAMPAIGN:
                result = await toolset.enable_campaign(campaign_id=rec.target)
            else:
                return "pending", {"note": "no executor for this action"}
        except Exception as exc:
            logger.warning("optimization_execute_failed", type=rec.type.value, error=str(exc))
            return "failed", {"error": str(exc)}
        return "executed", {"result": result}

    async def _notify(
        self, organization_id: uuid.UUID, decision: SafetyDecision, status: str
    ) -> None:
        rec = decision.recommendation
        if status == "executed":
            await self.notifications.create(
                organization_id=organization_id,
                type="optimization",
                severity="info",
                title=f"Optimization applied: {rec.type.value.replace('_', ' ')}",
                body=decision.explanation,
                data={"target": rec.target, "confidence": float(rec.confidence)},
            )
        elif status == "failed":
            await self.notifications.create(
                organization_id=organization_id,
                type="failure",
                severity="critical",
                title="Optimization action failed",
                body=decision.explanation,
                data={"target": rec.target},
            )


class OptimizationLogView:
    """Read helpers used by the API layer."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = OptimizationLogRepository(session)

    async def for_run(self, run_id: uuid.UUID) -> list[OptimizationLog]:
        return await self.repo.list_for_run(run_id)
