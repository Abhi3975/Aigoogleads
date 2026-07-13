"""Google Ads connection & linked-account models.

A ``GoogleAdsConnection`` stores the encrypted OAuth refresh token that a user
authorized for an organization. ``GoogleAdsAccount`` rows are the customer
accounts reachable through that connection.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class GoogleAdsConnection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "google_ads_connections"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authorized_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Fernet-encrypted OAuth refresh token (never stored in plaintext).
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Optional Google Ads manager (MCC) account id used as login-customer-id.
    login_customer_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # active | revoked | error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    accounts: Mapped[list[GoogleAdsAccount]] = relationship(
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<GoogleAdsConnection org={self.organization_id} status={self.status}>"


class GoogleAdsAccount(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "google_ads_accounts"
    __table_args__ = (
        UniqueConstraint("organization_id", "customer_id", name="uq_ads_account_org_customer"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("google_ads_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    descriptive_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    time_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_test_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enabled")

    connection: Mapped[GoogleAdsConnection] = relationship(back_populates="accounts")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<GoogleAdsAccount {self.customer_id} {self.descriptive_name!r}>"
