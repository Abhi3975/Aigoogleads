"""Aggregate v1 API router.

Feature routers are included here as milestones land (auth, organizations,
campaigns, keywords, agents, reports, …).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    ai,
    analytics,
    api_keys,
    auth,
    billing,
    campaigns,
    google_ads,
    health,
    industry,
    notifications,
    optimization,
    organizations,
    users,
)
from app.core.rate_limit import ai_rate_limit, auth_rate_limit

api_router = APIRouter()
api_router.include_router(health.router)
# Rate-limit sensitive surfaces (auth brute-force, cost-heavy AI calls).
api_router.include_router(auth.router, dependencies=[Depends(auth_rate_limit)])
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(google_ads.router)
api_router.include_router(google_ads.callback_router)
api_router.include_router(ai.router, dependencies=[Depends(ai_rate_limit)])
api_router.include_router(campaigns.router, dependencies=[Depends(ai_rate_limit)])
api_router.include_router(optimization.router, dependencies=[Depends(ai_rate_limit)])
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
api_router.include_router(industry.router)
api_router.include_router(api_keys.router)
api_router.include_router(api_keys.key_router)
api_router.include_router(billing.router)
