"""Structured I/O schemas for the AI agent system.

Every agent consumes and produces a typed Pydantic model; the LLM is always
asked for structured output validated against these schemas. Each output
carries a ``reasoning`` field so the agent's decision rationale is persisted.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
class BusinessContext(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    industry: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=4000)
    monthly_budget: float = Field(gt=0)
    goals: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    target_audience: str | None = None
    landing_url: str | None = None


# --------------------------------------------------------------------------
# Strategy
# --------------------------------------------------------------------------
class CampaignTheme(BaseModel):
    name: str
    description: str
    suggested_daily_budget: float | None = None


class StrategyOutput(BaseModel):
    summary: str
    objective: str
    recommended_daily_budget: float
    target_cpa: float | None = None
    target_roas: float | None = None
    campaign_themes: list[CampaignTheme] = Field(default_factory=list)
    reasoning: str


# --------------------------------------------------------------------------
# Keyword research
# --------------------------------------------------------------------------
class MatchType(str, enum.Enum):
    BROAD = "BROAD"
    PHRASE = "PHRASE"
    EXACT = "EXACT"


class KeywordItem(BaseModel):
    text: str
    match_type: MatchType = MatchType.PHRASE


class KeywordGroup(BaseModel):
    ad_group_name: str
    keywords: list[KeywordItem] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)


class KeywordResearchOutput(BaseModel):
    groups: list[KeywordGroup] = Field(default_factory=list)
    reasoning: str


# --------------------------------------------------------------------------
# Ad copy
# --------------------------------------------------------------------------
class ResponsiveSearchAd(BaseModel):
    ad_group_name: str
    headlines: list[str] = Field(default_factory=list, description="3-15 headlines, <=30 chars")
    descriptions: list[str] = Field(
        default_factory=list, description="2-4 descriptions, <=90 chars"
    )
    final_url: str
    path1: str | None = None
    path2: str | None = None


class AdCopyOutput(BaseModel):
    ads: list[ResponsiveSearchAd] = Field(default_factory=list)
    reasoning: str


# --------------------------------------------------------------------------
# Analytics / optimization / recommendations
# --------------------------------------------------------------------------
class AnalyticsOutput(BaseModel):
    summary: str
    insights: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    reasoning: str


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationType(str, enum.Enum):
    ADJUST_BUDGET = "adjust_budget"
    ADJUST_BID = "adjust_bid"
    PAUSE_CAMPAIGN = "pause_campaign"
    ENABLE_CAMPAIGN = "enable_campaign"
    ADD_KEYWORD = "add_keyword"
    ADD_NEGATIVE_KEYWORD = "add_negative_keyword"
    CREATE_CAMPAIGN = "create_campaign"
    OTHER = "other"


class Recommendation(BaseModel):
    type: RecommendationType
    target: str = Field(description="Campaign id or name the action applies to")
    rationale: str
    expected_impact: str
    risk_level: RiskLevel = RiskLevel.LOW
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    current_value: float | None = None
    proposed_value: float | None = None


class RecommendationOutput(BaseModel):
    summary: str
    recommendations: list[Recommendation] = Field(default_factory=list)
    reasoning: str


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
class ReportSection(BaseModel):
    heading: str
    body: str


class ReportOutput(BaseModel):
    title: str
    period: str
    summary: str
    highlights: list[str] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------
class AppliedAction(BaseModel):
    type: RecommendationType
    target: str
    tool: str | None = None
    status: str  # applied | skipped | failed
    detail: str | None = None


class ExecutionOutput(BaseModel):
    applied: list[AppliedAction] = Field(default_factory=list)
    summary: str


# --------------------------------------------------------------------------
# Supervisor aggregate
# --------------------------------------------------------------------------
class CampaignPlan(BaseModel):
    strategy: StrategyOutput
    keywords: KeywordResearchOutput
    ad_copy: AdCopyOutput
    recommendations: RecommendationOutput | None = None


class OptimizationResult(BaseModel):
    analytics: AnalyticsOutput
    recommendations: RecommendationOutput
    execution: ExecutionOutput | None = None


class OptimizeRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    date_range: str = "LAST_30_DAYS"
    auto_execute: bool = False


# --------------------------------------------------------------------------
# Run/step read models (decision log)
# --------------------------------------------------------------------------
class AgentStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    agent_name: str
    status: str
    reasoning: str | None = None
    output: dict | None = None
    tool_calls: list = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
    created_at: datetime


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow: str
    status: str
    input: dict = Field(default_factory=dict)
    output: dict | None = None
    error: str | None = None
    total_tokens: int = 0
    created_at: datetime


class AgentRunDetailOut(AgentRunOut):
    steps: list[AgentStepOut] = Field(default_factory=list)
