"""Optimization policy, log, and run schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OptimizationPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    auto_execute: bool
    max_budget_increase_pct: float
    max_budget_decrease_pct: float
    max_bid_change_pct: float
    min_days_active: int
    min_clicks_required: int
    min_keyword_clicks: int
    min_keyword_days: int
    min_confidence: float
    date_range: str


class OptimizationPolicyUpdate(BaseModel):
    enabled: bool | None = None
    auto_execute: bool | None = None
    max_budget_increase_pct: float | None = Field(default=None, ge=0, le=100)
    max_budget_decrease_pct: float | None = Field(default=None, ge=0, le=100)
    max_bid_change_pct: float | None = Field(default=None, ge=0, le=100)
    min_days_active: int | None = Field(default=None, ge=0)
    min_clicks_required: int | None = Field(default=None, ge=0)
    min_keyword_clicks: int | None = Field(default=None, ge=0)
    min_keyword_days: int | None = Field(default=None, ge=0)
    min_confidence: float | None = Field(default=None, ge=0, le=1)
    date_range: str | None = None


class OptimizationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: str | None = None
    campaign_id: str | None = None
    action_type: str
    target: str | None = None
    previous_value: float | None = None
    new_value: float | None = None
    reasoning: str | None = None
    explanation: str | None = None
    confidence: float
    status: str
    created_at: datetime


class OptimizationRunRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    date_range: str | None = None
    auto_execute: bool | None = None


class OptimizationRunSummary(BaseModel):
    run_id: uuid.UUID
    applied: int
    pending: int
    rejected: int
    failed: int
    logs: list[OptimizationLogOut]
