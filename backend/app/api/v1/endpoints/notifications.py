"""Notification endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentMembership, DbSession, PaginationParams
from app.core.exceptions import NotFoundError
from app.schemas.common import Message
from app.schemas.notification import NotificationOut, UnreadCount
from app.services.notification import NotificationService

router = APIRouter(prefix="/organizations/{organization_id}/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    pagination: PaginationParams,
    unread: bool = Query(False, description="Only unread notifications"),
) -> list[NotificationOut]:
    """List notifications for the organization (any member)."""
    items = await NotificationService(session).list(
        organization_id, unread_only=unread, offset=pagination.offset, limit=pagination.limit
    )
    return [NotificationOut.model_validate(n) for n in items]


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> UnreadCount:
    """Number of unread notifications (any member)."""
    return UnreadCount(unread=await NotificationService(session).unread_count(organization_id))


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    organization_id: uuid.UUID,
    notification_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
) -> NotificationOut:
    """Mark a notification as read (any member)."""
    notification = await NotificationService(session).mark_read(notification_id, organization_id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    return NotificationOut.model_validate(notification)


@router.post("/read-all", response_model=Message, status_code=status.HTTP_200_OK)
async def mark_all_read(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> Message:
    """Mark all notifications as read (any member)."""
    await NotificationService(session).mark_all_read(organization_id)
    return Message(message="All notifications marked as read.")
