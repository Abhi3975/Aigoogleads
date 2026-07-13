"""Audit logging service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestMeta
from app.repositories.audit import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AuditLogRepository(session)

    async def record(
        self,
        action: str,
        *,
        actor_user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        context: dict[str, Any] | None = None,
        meta: RequestMeta | None = None,
    ) -> None:
        await self.repo.create(
            action=action,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            context=context or {},
            ip_address=meta.ip_address if meta else None,
            user_agent=meta.user_agent if meta else None,
        )
