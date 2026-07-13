"""Aggregate v1 API router.

Feature routers are included here as milestones land (auth, organizations,
campaigns, keywords, agents, reports, …).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)
