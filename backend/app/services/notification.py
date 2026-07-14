"""Notification service (in-app records; email dispatch is best-effort)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        type: str,
        title: str,
        body: str = "",
        severity: str = "info",
        data: dict[str, Any] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Notification:
        notification = await self.repo.create(
            organization_id=organization_id,
            user_id=user_id,
            type=type,
            severity=severity,
            title=title,
            body=body,
            data=data or {},
        )
        await self.session.flush()
        return notification

    async def list(
        self,
        organization_id: uuid.UUID,
        *,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        return await self.repo.list_for_org(
            organization_id, unread_only=unread_only, offset=offset, limit=limit
        )

    async def unread_count(self, organization_id: uuid.UUID) -> int:
        return await self.repo.unread_count(organization_id)

    async def mark_read(
        self, notification_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Notification | None:
        notification = await self.repo.mark_read(notification_id, organization_id)
        await self.session.commit()
        return notification

    async def mark_all_read(self, organization_id: uuid.UUID) -> None:
        await self.repo.mark_all_read(organization_id)
        await self.session.commit()
