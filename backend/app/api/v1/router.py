"""Aggregate v1 API router.

Feature routers are included here as milestones land (auth, organizations,
campaigns, keywords, agents, reports, …).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    auth,
    campaigns,
    google_ads,
    health,
    organizations,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(google_ads.router)
api_router.include_router(google_ads.callback_router)
api_router.include_router(ai.router)
api_router.include_router(campaigns.router)
