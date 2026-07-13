"""GAQL (Google Ads Query Language) builders.

Date ranges are validated against an allow-list to prevent GAQL injection —
never interpolate untrusted input into a query string otherwise.
"""

from __future__ import annotations

from app.core.exceptions import ValidationError

# Google Ads predefined date ranges we expose.
ALLOWED_DATE_RANGES = frozenset(
    {
        "TODAY",
        "YESTERDAY",
        "LAST_7_DAYS",
        "LAST_14_DAYS",
        "LAST_30_DAYS",
        "THIS_MONTH",
        "LAST_MONTH",
        "LAST_BUSINESS_WEEK",
        "THIS_WEEK_SUN_TODAY",
        "LAST_WEEK_SUN_SAT",
    }
)

CAMPAIGNS_QUERY = (
    "SELECT campaign.id, campaign.name, campaign.status, "
    "campaign.advertising_channel_type, campaign.bidding_strategy_type, "
    "campaign_budget.amount_micros "
    "FROM campaign "
    "WHERE campaign.status != 'REMOVED' "
    "ORDER BY campaign.id"
)

CUSTOMER_QUERY = (
    "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
    "customer.time_zone, customer.manager, customer.test_account "
    "FROM customer LIMIT 1"
)


def validate_date_range(date_range: str) -> str:
    normalized = date_range.strip().upper()
    if normalized not in ALLOWED_DATE_RANGES:
        raise ValidationError(
            f"Unsupported date range '{date_range}'.",
            details={"allowed": sorted(ALLOWED_DATE_RANGES)},
        )
    return normalized


def campaign_metrics_query(date_range: str) -> str:
    dr = validate_date_range(date_range)
    return (
        "SELECT campaign.id, campaign.name, metrics.impressions, metrics.clicks, "
        "metrics.cost_micros, metrics.conversions, metrics.conversions_value, "
        "metrics.ctr, metrics.average_cpc "
        "FROM campaign "
        f"WHERE segments.date DURING {dr} AND campaign.status != 'REMOVED'"
    )
