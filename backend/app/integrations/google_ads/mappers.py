"""Pure mappers from Google Ads API rows to application schemas.

Kept free of SDK imports so they can be unit-tested with lightweight stand-ins
(any object exposing the same attribute paths).
"""

from __future__ import annotations

from typing import Any

from app.schemas.google_ads import CampaignMetricsOut, CampaignOut

_MICROS = 1_000_000


def enum_name(value: Any) -> str:
    """Return an enum's name whether it's a proto-plus enum or a plain string."""
    if value is None:
        return ""
    return getattr(value, "name", None) or str(value)


def micros_to_units(micros: Any) -> float:
    try:
        return round(int(micros) / _MICROS, 2)
    except (TypeError, ValueError):
        return 0.0


def map_campaign(row: Any) -> CampaignOut:
    campaign = row.campaign
    budget_micros = getattr(getattr(row, "campaign_budget", None), "amount_micros", None)
    return CampaignOut(
        id=str(campaign.id),
        name=campaign.name,
        status=enum_name(campaign.status),
        channel_type=enum_name(campaign.advertising_channel_type),
        bidding_strategy_type=enum_name(getattr(campaign, "bidding_strategy_type", None)) or None,
        daily_budget=micros_to_units(budget_micros) if budget_micros is not None else None,
    )


def map_metrics(row: Any) -> CampaignMetricsOut:
    campaign = row.campaign
    m = row.metrics
    impressions = int(getattr(m, "impressions", 0) or 0)
    clicks = int(getattr(m, "clicks", 0) or 0)
    cost = micros_to_units(getattr(m, "cost_micros", 0))
    conversions = float(getattr(m, "conversions", 0.0) or 0.0)
    conv_value = float(getattr(m, "conversions_value", 0.0) or 0.0)
    ctr = round(float(getattr(m, "ctr", 0.0) or 0.0), 4)
    avg_cpc = micros_to_units(getattr(m, "average_cpc", 0))
    cost_per_conv = round(cost / conversions, 2) if conversions else 0.0
    roas = round(conv_value / cost, 2) if cost else 0.0
    return CampaignMetricsOut(
        campaign_id=str(campaign.id),
        campaign_name=campaign.name,
        impressions=impressions,
        clicks=clicks,
        cost=cost,
        conversions=conversions,
        conversions_value=conv_value,
        ctr=ctr,
        average_cpc=avg_cpc,
        cost_per_conversion=cost_per_conv,
        roas=roas,
    )


def map_customer(row: Any) -> dict[str, Any]:
    c = row.customer
    return {
        "customer_id": str(c.id),
        "descriptive_name": getattr(c, "descriptive_name", None),
        "currency_code": getattr(c, "currency_code", None),
        "time_zone": getattr(c, "time_zone", None),
        "is_manager": bool(getattr(c, "manager", False)),
        "is_test_account": bool(getattr(c, "test_account", False)),
    }
