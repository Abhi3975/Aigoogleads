"""Organization API keys for programmatic access."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class APIKey(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Displayable non-secret prefix + SHA-256 of the full key (secret never stored).
    prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    scopes: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
