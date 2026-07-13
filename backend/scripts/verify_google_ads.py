"""Live Google Ads connectivity check.

Run this against a real (test) Google Ads account to verify credentials and the
API client end-to-end, without going through the web OAuth flow.

Prerequisites (env or backend/.env):
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_ADS_DEVELOPER_TOKEN
    GOOGLE_ADS_LOGIN_CUSTOMER_ID   (optional; manager account id, digits only)
    GOOGLE_ADS_REFRESH_TOKEN       (an OAuth refresh token with the adwords scope)

Usage:
    uv run python scripts/verify_google_ads.py [CUSTOMER_ID]

If CUSTOMER_ID is omitted, the script lists accessible accounts and uses the
first non-manager account for the campaign/metrics checks.
"""

from __future__ import annotations

import os
import sys

from app.integrations.google_ads.client import create_wrapper
from app.integrations.google_ads.mappers import map_campaign, map_customer, map_metrics
from app.integrations.google_ads.queries import CAMPAIGNS_QUERY, campaign_metrics_query


def main() -> int:
    refresh_token = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN")
    if not refresh_token:
        print("ERROR: set GOOGLE_ADS_REFRESH_TOKEN (adwords-scoped refresh token).")
        return 2

    login_cid = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or None
    wrapper = create_wrapper(refresh_token=refresh_token, login_customer_id=login_cid)

    print("→ Listing accessible customers…")
    customer_ids = wrapper.list_accessible_customers()
    print(f"  accessible customers: {customer_ids}")
    if not customer_ids:
        print("No accessible customers. Check developer token approval / account access.")
        return 1

    target = sys.argv[1] if len(sys.argv) > 1 else customer_ids[0]
    print(f"→ Fetching customer details for {target}…")
    row = wrapper.get_customer(target)
    if row is not None:
        print(f"  {map_customer(row)}")

    print(f"→ Reading campaigns for {target}…")
    campaigns = [map_campaign(r) for r in wrapper.search(target, CAMPAIGNS_QUERY)]
    for c in campaigns:
        print(f"  [{c.status}] {c.id} {c.name} (budget/day={c.daily_budget})")
    if not campaigns:
        print("  (no campaigns yet)")

    print(f"→ Reading LAST_30_DAYS metrics for {target}…")
    metrics = [
        map_metrics(r) for r in wrapper.search(target, campaign_metrics_query("LAST_30_DAYS"))
    ]
    for m in metrics:
        print(
            f"  {m.campaign_name}: impr={m.impressions} clicks={m.clicks} "
            f"cost={m.cost} conv={m.conversions} roas={m.roas}"
        )

    print("\n✅ Google Ads integration verified against the live account.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
