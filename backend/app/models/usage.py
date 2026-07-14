"""Per-organization usage metering records (monthly counters per feature)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UsageRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "feature", "period", name="uq_usage_org_feature_period"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # e.g. "ai_run", "campaign_created"
    feature: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    # Billing period as "YYYY-MM".
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
