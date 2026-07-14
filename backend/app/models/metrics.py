"""Historical Google Ads performance metrics (campaign / keyword / ad) and
daily aggregate reports."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CampaignMetric(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "customer_id", "campaign_id", "date", name="uq_campaign_metric_day"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    conversions: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    conversions_value: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    average_cpc: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    cpa: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    roas: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class KeywordMetric(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "keyword_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "customer_id",
            "ad_group_id",
            "criterion_id",
            "date",
            name="uq_keyword_metric_day",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    ad_group_id: Mapped[str] = mapped_column(String(40), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(40), nullable=False)
    keyword_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    conversions: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    cost_per_conversion: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class AdMetric(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ad_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "customer_id", "ad_id", "date", name="uq_ad_metric_day"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(40), nullable=False)
    ad_group_id: Mapped[str] = mapped_column(String(40), nullable=False)
    ad_id: Mapped[str] = mapped_column(String(40), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    conversions: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class DailyPerformanceReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "daily_performance_reports"
    __table_args__ = (
        UniqueConstraint("organization_id", "customer_id", "date", name="uq_daily_report"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    totals: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
