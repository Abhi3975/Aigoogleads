"""Notification repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.organization_id == organization_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def unread_count(self, organization_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.is_read.is_(False),
            )
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def mark_read(
        self, notification_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Notification | None:
        notification = await self.get_by(id=notification_id, organization_id=organization_id)
        if notification is None:
            return None
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        await self.session.flush()
        return notification

    async def mark_all_read(self, organization_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        await self.session.flush()
