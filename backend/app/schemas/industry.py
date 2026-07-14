"""Industry template schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndustryTemplate(BaseModel):
    industry: str
    display_name: str
    recommended_campaign_type: str
    objective: str
    bidding_strategy: str
    keyword_themes: list[str] = Field(default_factory=list)
    ad_angles: list[str] = Field(default_factory=list)
    suggested_negative_keywords: list[str] = Field(default_factory=list)
    budget_guidance: str
