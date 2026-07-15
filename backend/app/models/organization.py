"""Organization (tenant) and membership models — multi-tenancy + RBAC."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import OrgPlan, OrgRole

if TYPE_CHECKING:
    from app.models.user import User


class Organization(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    plan: Mapped[OrgPlan] = mapped_column(
        SAEnum(OrgPlan, name="org_plan", native_enum=True),
        default=OrgPlan.FREE,
        nullable=False,
    )

    # Free-form tenant settings (safety limits, defaults, feature flags, …).
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Stripe billing linkage (set once a subscription is created).
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Organization {self.slug}>"


class OrganizationMembership(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[OrgRole] = mapped_column(
        SAEnum(OrgRole, name="org_role", native_enum=True),
        default=OrgRole.VIEWER,
        nullable=False,
    )

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Membership org={self.organization_id} user={self.user_id} role={self.role}>"
