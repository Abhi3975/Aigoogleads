"""Execution agent — enacts approved recommendations via the Google Ads tools.

This agent is deterministic (not LLM-driven): it maps structured, approved
recommendations to concrete tool calls, applying strict safety filters so
autonomous execution stays within bounds. Every action is logged.
"""

from __future__ import annotations

from app.agents.context import RunContext
from app.agents.tools import GoogleAdsToolset
from app.core.logging import get_logger
from app.schemas.agents import (
    AppliedAction,
    ExecutionOutput,
    Recommendation,
    RecommendationOutput,
    RecommendationType,
    RiskLevel,
)

logger = get_logger(__name__)

# Recommendation types this agent is allowed to enact autonomously.
_SUPPORTED = {
    RecommendationType.ADJUST_BUDGET,
    RecommendationType.PAUSE_CAMPAIGN,
    RecommendationType.ENABLE_CAMPAIGN,
}


class ExecutionAgent:
    name = "execution"

    def __init__(self, toolset: GoogleAdsToolset) -> None:
        self.toolset = toolset

    async def run(
        self,
        ctx: RunContext,
        recommendations: RecommendationOutput,
        *,
        max_actions: int = 5,
        min_confidence: float = 0.6,
        max_risk: RiskLevel = RiskLevel.MEDIUM,
    ) -> ExecutionOutput:
        applied: list[AppliedAction] = []
        tool_calls: list[dict] = []
        risk_rank = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}

        for rec in recommendations.recommendations[:max_actions]:
            if rec.type not in _SUPPORTED:
                applied.append(
                    self._skip(rec, "action type not supported for autonomous execution")
                )
                continue
            if rec.confidence < min_confidence:
                applied.append(self._skip(rec, f"confidence {rec.confidence} below threshold"))
                continue
            if risk_rank[rec.risk_level] > risk_rank[max_risk]:
                applied.append(self._skip(rec, f"risk {rec.risk_level.value} exceeds limit"))
                continue

            action, call = await self._apply(rec)
            applied.append(action)
            tool_calls.append(call)

        output = ExecutionOutput(
            applied=applied,
            summary=(
                f"Applied {sum(1 for a in applied if a.status == 'applied')} of "
                f"{len(applied)} evaluated recommendations."
            ),
        )
        await ctx.log_step(
            agent_name=self.name,
            input=recommendations,
            output=output,
            reasoning="Deterministic execution of approved, in-policy recommendations.",
            tool_calls=tool_calls,
        )
        return output

    async def _apply(self, rec: Recommendation) -> tuple[AppliedAction, dict]:
        try:
            campaign_id = str(int(rec.target))  # budget/pause/enable target must be an id
        except ValueError:
            return (
                self._skip(rec, "target is not a numeric campaign id"),
                {"tool": None, "target": rec.target, "error": "non-numeric target"},
            )

        try:
            if rec.type is RecommendationType.ADJUST_BUDGET:
                if rec.proposed_value is None:
                    return self._skip(rec, "no proposed budget"), {"tool": "update_budget"}
                result = await self.toolset.update_budget(
                    campaign_id=campaign_id, daily_budget=rec.proposed_value
                )
                tool = "update_budget"
            elif rec.type is RecommendationType.PAUSE_CAMPAIGN:
                result = await self.toolset.pause_campaign(campaign_id=campaign_id)
                tool = "pause_campaign"
            else:  # ENABLE_CAMPAIGN
                result = await self.toolset.enable_campaign(campaign_id=campaign_id)
                tool = "enable_campaign"
        except Exception as exc:
            logger.warning("execution_action_failed", type=rec.type.value, error=str(exc))
            return (
                AppliedAction(
                    type=rec.type, target=rec.target, tool=None, status="failed", detail=str(exc)
                ),
                {"tool": rec.type.value, "target": campaign_id, "error": str(exc)},
            )

        return (
            AppliedAction(
                type=rec.type, target=rec.target, tool=tool, status="applied", detail=str(result)
            ),
            {"tool": tool, "target": campaign_id, "result": result},
        )

    @staticmethod
    def _skip(rec: Recommendation, reason: str) -> AppliedAction:
        return AppliedAction(
            type=rec.type, target=rec.target, tool=None, status="skipped", detail=reason
        )
