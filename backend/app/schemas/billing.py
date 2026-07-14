"""Billing / plan schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import OrgPlan


class PlanInfo(BaseModel):
    plan: str
    limits: dict[str, int]


class BillingStatus(BaseModel):
    plan: str
    limits: dict[str, int]
    usage: dict[str, int] = Field(default_factory=dict)


class PlanChange(BaseModel):
    plan: OrgPlan
