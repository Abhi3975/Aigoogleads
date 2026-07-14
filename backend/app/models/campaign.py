"""Campaign-creation domain models.

Onboarding (business profile, budget, audience, products), website analysis,
the AI-generated campaign blueprint, and per-action execution logs.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class BusinessProfile(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "business_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str] = mapped_column(String(160), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    product_service_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    usp: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    target_countries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    target_cities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Marketing goal, e.g. generate_leads / increase_sales / website_traffic / ...
    goal: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    budget: Mapped[BudgetConfiguration | None] = relationship(
        back_populates="business_profile", uselist=False, cascade="all, delete-orphan"
    )
    audience: Mapped[AudienceProfile | None] = relationship(
        back_populates="business_profile", uselist=False, cascade="all, delete-orphan"
    )
    products: Mapped[list[ProductInformation]] = relationship(
        back_populates="business_profile", cascade="all, delete-orphan"
    )


class BudgetConfiguration(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budget_configurations"

    business_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    daily_budget: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    monthly_budget: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    max_cpa: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_roas: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    business_profile: Mapped[BusinessProfile] = relationship(back_populates="budget")


class AudienceProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audience_profiles"

    business_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    locations: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    pain_points: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    existing_customer_profile: Mapped[str | None] = mapped_column(Text, nullable=True)

    business_profile: Mapped[BusinessProfile] = relationship(back_populates="audience")


class ProductInformation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_information"

    business_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pricing: Mapped[str | None] = mapped_column(String(120), nullable=True)
    features: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    benefits: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    landing_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    business_profile: Mapped[BusinessProfile] = relationship(back_populates="products")


class WebsiteAnalysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "website_analyses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    business_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    products: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    services: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    target_customer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    selling_points: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    recommended_strategy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")


class CampaignBlueprint(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An AI-generated, immutable campaign plan snapshot ready for execution."""

    __tablename__ = "campaign_blueprints"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_profiles.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )

    customer_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(40), nullable=False)
    objective: Mapped[str] = mapped_column(String(120), nullable=False)
    daily_budget: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    bidding_strategy: Mapped[str] = mapped_column(String(60), nullable=False)

    # Full plan: ad groups w/ keywords, negatives, ads, and extensions.
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # draft | approved | executing | created | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    google_campaign_id: Mapped[str | None] = mapped_column(String(40), nullable=True)

    execution_logs: Mapped[list[CampaignExecutionLog]] = relationship(
        back_populates="blueprint",
        cascade="all, delete-orphan",
        order_by="CampaignExecutionLog.sequence",
    )


class CampaignExecutionLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_execution_logs"

    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    google_resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # success | failed | skipped | rolled_back
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    blueprint: Mapped[CampaignBlueprint] = relationship(back_populates="execution_logs")
