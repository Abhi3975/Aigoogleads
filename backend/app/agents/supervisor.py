"""Supervisor agent — coordinates the specialized agents into workflows.

The supervisor owns two workflows:
- ``plan_campaigns``: strategy -> keyword research -> ad copy (+ stored in memory)
- ``optimize``: gather data via tools -> analytics -> recommendations -> (execute)

It is framework-agnostic; the same node sequence can be hosted by LangGraph. It
persists the business profile and latest strategy to durable memory.
"""

from __future__ import annotations

from app.agents.context import RunContext
from app.agents.execution import ExecutionAgent
from app.agents.specialists import (
    AdCopyAgent,
    AnalyticsAgent,
    CampaignStrategyAgent,
    KeywordResearchAgent,
    RecommendationAgent,
)
from app.agents.tools import GoogleAdsToolset
from app.schemas.agents import BusinessContext, CampaignPlan, OptimizationResult

MEMORY_BUSINESS = "business_profile"
MEMORY_STRATEGY = "strategy"


class SupervisorAgent:
    name = "supervisor"

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    async def plan_campaigns(self, business: BusinessContext) -> CampaignPlan:
        business_dict = business.model_dump(mode="json")
        await self.ctx.remember(MEMORY_BUSINESS, "current", business_dict)

        strategy = await CampaignStrategyAgent().run(self.ctx, {"business": business_dict})
        keywords = await KeywordResearchAgent().run(
            self.ctx, {"business": business_dict, "strategy": strategy.model_dump(mode="json")}
        )
        ad_copy = await AdCopyAgent().run(
            self.ctx, {"business": business_dict, "keywords": keywords.model_dump(mode="json")}
        )

        await self.ctx.remember(MEMORY_STRATEGY, "latest", strategy.model_dump(mode="json"))
        return CampaignPlan(strategy=strategy, keywords=keywords, ad_copy=ad_copy)

    async def optimize(
        self,
        toolset: GoogleAdsToolset,
        *,
        date_range: str = "LAST_30_DAYS",
        auto_execute: bool = False,
    ) -> OptimizationResult:
        # 1) Gather performance data through the Google Ads tools.
        campaigns = await toolset.get_campaigns()
        metrics = await toolset.get_metrics(date_range)
        await self.ctx.log_step(
            agent_name=self.name,
            input={"date_range": date_range, "customer_id": toolset.customer_id},
            output={"campaigns": len(campaigns), "metrics": len(metrics)},
            reasoning="Gathered campaigns and performance metrics via Google Ads tools.",
            tool_calls=[
                {"tool": "get_campaigns"},
                {"tool": "get_metrics", "arguments": {"date_range": date_range}},
            ],
        )

        # 2) Analyze -> recommend.
        analytics = await AnalyticsAgent().run(
            self.ctx, {"metrics": metrics, "campaigns": campaigns}
        )
        recommendations = await RecommendationAgent().run(
            self.ctx, {"analytics": analytics.model_dump(mode="json"), "metrics": metrics}
        )

        # 3) Optionally enact approved, in-policy recommendations.
        execution = None
        if auto_execute:
            execution = await ExecutionAgent(toolset).run(self.ctx, recommendations)

        return OptimizationResult(
            analytics=analytics, recommendations=recommendations, execution=execution
        )
