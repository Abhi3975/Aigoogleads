"""Analytics read schemas (aggregated performance)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class KpiTotals(BaseModel):
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    conversions: float = 0.0
    conversions_value: float = 0.0
    ctr: float = 0.0
    average_cpc: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    conversion_rate: float = 0.0


class CampaignPerformance(BaseModel):
    campaign_id: str
    campaign_name: str | None = None
    cost: float = 0.0
    clicks: int = 0
    conversions: float = 0.0
    ctr: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0


class AnalyticsSummary(BaseModel):
    as_of: date | None = None
    totals: KpiTotals
    campaigns: list[CampaignPerformance]


class TimeseriesPoint(BaseModel):
    date: date
    cost: float = 0.0
    clicks: int = 0
    conversions: float = 0.0
    conversions_value: float = 0.0


class AnalyticsTimeseries(BaseModel):
    points: list[TimeseriesPoint]
