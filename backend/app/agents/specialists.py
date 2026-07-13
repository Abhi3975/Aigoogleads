"""Specialized LLM agents.

Each agent has a focused responsibility, a strict output schema, and a system
prompt establishing its expertise. They are coordinated by the Supervisor.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.agents import (
    AdCopyOutput,
    AnalyticsOutput,
    KeywordResearchOutput,
    RecommendationOutput,
    ReportOutput,
    StrategyOutput,
)


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)


class CampaignStrategyAgent(BaseAgent[StrategyOutput]):
    name = "campaign_strategy"
    description = "Designs the overall Google Ads strategy from business context."
    output_model = StrategyOutput
    temperature = 0.5
    system_prompt = (
        "You are a senior Google Ads strategist. Given a business profile, design a "
        "pragmatic, budget-aware advertising strategy: a clear objective, a sensible "
        "daily budget derived from the monthly budget, target CPA/ROAS where inferable, "
        "and 2-5 distinct campaign themes. Be specific and realistic. Always explain your "
        "reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return "Business profile:\n" + _dumps(payload["business"])


class KeywordResearchAgent(BaseAgent[KeywordResearchOutput]):
    name = "keyword_research"
    description = "Produces ad groups with keywords, match types, and negatives."
    output_model = KeywordResearchOutput
    temperature = 0.4
    system_prompt = (
        "You are a Google Ads keyword research specialist. Given the business and the "
        "chosen strategy, produce tightly-themed ad groups. For each ad group provide "
        "relevant keywords with appropriate match types (BROAD/PHRASE/EXACT) and useful "
        "negative keywords to exclude irrelevant traffic. Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "Business profile:\n"
            + _dumps(payload["business"])
            + "\n\nStrategy:\n"
            + _dumps(payload["strategy"])
        )


class AdCopyAgent(BaseAgent[AdCopyOutput]):
    name = "ad_copy"
    description = "Writes Responsive Search Ads for each ad group."
    output_model = AdCopyOutput
    temperature = 0.7
    system_prompt = (
        "You are an expert Google Ads copywriter. For each ad group, write one Responsive "
        "Search Ad with 8-15 unique headlines (<=30 characters each) and 3-4 descriptions "
        "(<=90 characters each). Copy must be compelling, benefit-led, policy-compliant, and "
        "include relevant keywords. Provide a final_url for each ad. Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "Business profile:\n"
            + _dumps(payload["business"])
            + "\n\nAd groups & keywords:\n"
            + _dumps(payload["keywords"])
        )


class BudgetOptimizationAgent(BaseAgent[RecommendationOutput]):
    name = "budget_optimization"
    description = "Proposes budget and bid adjustments from performance data."
    output_model = RecommendationOutput
    temperature = 0.3
    system_prompt = (
        "You are a Google Ads budget & bidding optimization expert. Given campaign metrics "
        "and targets, propose concrete budget and bid adjustments. Favour reallocating spend "
        "toward efficient campaigns (low CPA / high ROAS) and reducing waste. For each "
        "recommendation set current_value and proposed_value where applicable, a risk_level "
        "and a confidence score. Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return "Metrics & context:\n" + _dumps(payload)


class AnalyticsAgent(BaseAgent[AnalyticsOutput]):
    name = "analytics"
    description = "Analyzes performance metrics into insights and anomalies."
    output_model = AnalyticsOutput
    temperature = 0.3
    system_prompt = (
        "You are a Google Ads performance analyst. Given campaign metrics, summarise "
        "performance, surface the most important insights, and flag anomalies (e.g. spend "
        "with no conversions, sudden CTR drops, high CPA). Be quantitative and concise. "
        "Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return "Performance data:\n" + _dumps(payload)


class RecommendationAgent(BaseAgent[RecommendationOutput]):
    name = "recommendation"
    description = "Turns analysis into prioritized, actionable recommendations."
    output_model = RecommendationOutput
    temperature = 0.3
    system_prompt = (
        "You are a Google Ads optimization advisor. Given the analytics summary and metrics, "
        "produce prioritized, actionable recommendations (adjust_budget, adjust_bid, "
        "pause_campaign, enable_campaign, add_keyword, add_negative_keyword, create_campaign). "
        "Each must reference a target campaign, an expected_impact, a risk_level and a "
        "confidence score. Only recommend high-confidence, safe actions. Explain your reasoning."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return (
            "Analytics:\n"
            + _dumps(payload["analytics"])
            + "\n\nMetrics:\n"
            + _dumps(payload.get("metrics", []))
        )


class ReportingAgent(BaseAgent[ReportOutput]):
    name = "reporting"
    description = "Produces a human-readable performance report."
    output_model = ReportOutput
    temperature = 0.4
    system_prompt = (
        "You are a Google Ads reporting specialist. Produce a clear, executive-ready report "
        "from the metrics and analysis: a title, the reporting period, a concise summary, key "
        "highlights, and a few well-structured sections. Write for a business owner, not an "
        "engineer."
    )

    def build_prompt(self, payload: dict[str, Any]) -> str:
        return "Report inputs:\n" + _dumps(payload)
