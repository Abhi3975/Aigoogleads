"""Agents for the autonomous campaign-creation workflow.

- WebsiteAnalysisAgent — extracts business intelligence from a website.
- StrategyArchitectAgent — designs the campaign type and ad-group structure.
- KeywordPlannerAgent — produces intent-grouped keywords + negatives.
- AdCreativeAgent — writes Google Ads-compliant RSAs + extensions.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.campaign import (
    AdCreativeOutput,
    CampaignStrategyPlan,
    KeywordPlanOutput,
    WebsiteAnalysisOutput,
)


def _dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


class WebsiteAnalysisAgent(BaseAgent[WebsiteAnalysisOutput]):
    name = "website_analysis"
    description = "Extracts business intelligence from website content."
    output_model = WebsiteAnalysisOutput
    temperature = 0.3
    system_prompt = (
        "You are a marketing analyst. Given the text content of a business website, "
        "extract a concise business summary, the products and services offered, the likely "
        "target customer, high-value keywords the business should target, its key selling "
        "points, notable competitors if inferable, an assessment of landing-page quality, and "
        "a recommended advertising strategy. Be accurate and avoid inventing facts not "
        "supported by the content. Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            f"URL: {payload['url']}\n"
            f"Title: {payload.get('title', '')}\n"
            f"Meta description: {payload.get('description', '')}\n\n"
            f"Page content:\n{payload.get('content', '')}"
        )


class StrategyArchitectAgent(BaseAgent[CampaignStrategyPlan]):
    name = "strategy_architect"
    description = "Designs the campaign type, budget, bidding, and ad-group structure."
    output_model = CampaignStrategyPlan
    temperature = 0.4
    system_prompt = (
        "You are a senior Google Ads strategist. Using the business profile, marketing goal, "
        "budget, audience, and website analysis, design a concrete campaign plan: choose the "
        "most suitable campaign type (SEARCH, DISPLAY, PERFORMANCE_MAX, or SHOPPING) for the "
        "goal, a sensible daily budget within the provided budget, an appropriate bidding "
        "strategy, location targeting, audience targeting, and 2-5 tightly-themed ad groups. "
        "Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "Business profile:\n"
            + _dumps(payload["business"])
            + "\n\nMarketing goal: "
            + str(payload["goal"])
            + "\n\nBudget:\n"
            + _dumps(payload["budget"])
            + "\n\nAudience:\n"
            + _dumps(payload.get("audience"))
            + "\n\nWebsite analysis:\n"
            + _dumps(payload.get("website_analysis"))
        )


class KeywordPlannerAgent(BaseAgent[KeywordPlanOutput]):
    name = "keyword_planner"
    description = "Generates intent-grouped keywords and negative keywords per ad group."
    output_model = KeywordPlanOutput
    temperature = 0.4
    system_prompt = (
        "You are a Google Ads keyword research expert. For each ad group in the strategy, "
        "generate a mix of high-intent transactional keywords (e.g. 'buy X online'), "
        "commercial keywords (e.g. 'best X'), and a few informational long-tail keywords, each "
        "with an appropriate match type (BROAD/PHRASE/EXACT) and intent label. Also provide "
        "negative keywords per group and shared negatives to exclude irrelevant traffic. "
        "Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "Business profile:\n"
            + _dumps(payload["business"])
            + "\n\nStrategy & ad groups:\n"
            + _dumps(payload["strategy"])
        )


class AdCreativeAgent(BaseAgent[AdCreativeOutput]):
    name = "ad_creative"
    description = "Writes Responsive Search Ads and ad extensions."
    output_model = AdCreativeOutput
    temperature = 0.7
    system_prompt = (
        "You are an expert Google Ads copywriter. For each ad group, write one Responsive "
        "Search Ad with 15 unique headlines (each <=30 characters) and 4 descriptions (each "
        "<=90 characters). Copy must be compelling, benefit-led, Google Ads policy-compliant, "
        "and free of misleading claims, excessive capitalisation, or unsupported superlatives. "
        "Include a final_url for each ad. Also propose sitelink and callout extensions at the "
        "campaign level. Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "Business profile:\n"
            + _dumps(payload["business"])
            + "\n\nAd groups & keywords:\n"
            + _dumps(payload["keywords"])
            + "\n\nStrategy:\n"
            + _dumps(payload["strategy"])
        )
