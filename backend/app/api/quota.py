"""Plan-quota enforcement dependencies for metered endpoints."""

from __future__ import annotations

import uuid

from fastapi import Path

from app.api.deps import DbSession
from app.services.usage import UsageService


async def consume_ai_quota(
    session: DbSession,
    organization_id: uuid.UUID = Path(...),
) -> None:
    """Enforce (and meter) the organization's monthly AI-run quota."""
    await UsageService(session).consume(organization_id, "ai_run")
