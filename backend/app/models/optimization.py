"""Optimization safety policy and per-action optimization audit log."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class OptimizationPolicy(UUIDMixin, TimestampMixin, Base):
    """Per-organization safety rules governing autonomous optimization."""

    __tablename__ = "optimization_policies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Autonomous loop toggles.
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_execute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Budget / bid change caps (percent).
    max_budget_increase_pct: Mapped[float] = mapped_column(
        Numeric(6, 2), default=20, nullable=False
    )
    max_budget_decrease_pct: Mapped[float] = mapped_column(
        Numeric(6, 2), default=30, nullable=False
    )
    max_bid_change_pct: Mapped[float] = mapped_column(Numeric(6, 2), default=25, nullable=False)

    # Minimum data thresholds before pausing.
    min_days_active: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    min_clicks_required: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    min_keyword_clicks: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    min_keyword_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)

    min_confidence: Mapped[float] = mapped_column(Numeric(4, 2), default=0.6, nullable=False)
    date_range: Mapped[str] = mapped_column(String(40), default="LAST_30_DAYS", nullable=False)


class OptimizationLog(UUIDMixin, TimestampMixin, Base):
    """Explainable audit record for every optimization decision/action."""

    __tablename__ = "optimization_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    customer_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    campaign_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    action_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    new_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(4, 2), default=0, nullable=False)

    # approved | rejected | executed | failed | pending
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    api_response: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
