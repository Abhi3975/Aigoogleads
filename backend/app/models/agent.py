"""AI agent persistence: runs, steps (decision/reasoning logs), and memory."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AgentRun(UUIDMixin, TimestampMixin, Base):
    """A single supervised workflow execution (e.g. campaign planning)."""

    __tablename__ = "agent_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    workflow: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # pending | running | completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    input: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.sequence",
    )


class AgentStep(UUIDMixin, TimestampMixin, Base):
    """A single agent invocation within a run — the decision/reasoning record."""

    __tablename__ = "agent_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")

    input: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    run: Mapped[AgentRun] = relationship(back_populates="steps")


class AgentMemory(UUIDMixin, TimestampMixin, Base):
    """Durable, organization-scoped key/value memory for agents."""

    __tablename__ = "agent_memories"
    __table_args__ = (
        UniqueConstraint("organization_id", "namespace", "key", name="uq_agent_memory_org_ns_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Importance drives retrieval ranking (higher = surfaced first, kept longer).
    importance_score: Mapped[float] = mapped_column(Numeric(4, 2), default=0.5, nullable=False)


class AIInsight(UUIDMixin, TimestampMixin, Base):
    """A durable learning/observation the AI recorded from outcomes."""

    __tablename__ = "ai_insights"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # optimization | performance | hypothesis | anomaly | strategy | ...
    insight_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[float] = mapped_column(Numeric(4, 2), default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 2), default=0.5, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
