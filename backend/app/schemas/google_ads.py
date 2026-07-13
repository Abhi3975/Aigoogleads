"""Google Ads integration schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoogleAdsAuthURL(BaseModel):
    authorization_url: str
    state: str


class GoogleAdsAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    descriptive_name: str | None = None
    currency_code: str | None = None
    time_zone: str | None = None
    is_manager: bool = False
    is_test_account: bool = False


class GoogleAdsConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    status: str
    login_customer_id: str | None = None
    last_synced_at: datetime | None = None
    accounts_count: int = 0


class CampaignOut(BaseModel):
    id: str
    name: str
    status: str
    channel_type: str
    bidding_strategy_type: str | None = None
    daily_budget: float | None = Field(default=None, description="Daily budget in account currency")


class CampaignMetricsOut(BaseModel):
    campaign_id: str
    campaign_name: str
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    conversions_value: float = 0.0
    ctr: float = 0.0
    average_cpc: float = 0.0
    cost_per_conversion: float = 0.0
    roas: float = 0.0


class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    daily_budget: float = Field(gt=0, description="Daily budget in account currency units")
    # Test campaigns are created PAUSED by default to avoid unintended spend.
    start_paused: bool = True


class CreateCampaignResult(BaseModel):
    campaign_id: str
    campaign_resource_name: str
    budget_resource_name: str
    status: str
