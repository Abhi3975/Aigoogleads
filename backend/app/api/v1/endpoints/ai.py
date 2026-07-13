"""AI agent endpoints — run workflows and inspect decision logs & memory."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentMembership,
    CurrentUser,
    DbSession,
    PaginationParams,
    RequestMetadata,
    require_role,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import OrgRole, role_rank
from app.models.organization import OrganizationMembership
from app.schemas.agents import (
    AgentRunDetailOut,
    AgentRunOut,
    BusinessContext,
    OptimizeRequest,
)
from app.services.ai import AIService

router = APIRouter(prefix="/organizations/{organization_id}/ai", tags=["ai-agents"])


@router.post("/plan", response_model=AgentRunDetailOut, status_code=status.HTTP_201_CREATED)
async def run_campaign_plan(
    organization_id: uuid.UUID,
    business: BusinessContext,
    current_user: CurrentUser,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ANALYST)),
) -> AgentRunDetailOut:
    """Run the multi-agent campaign-planning workflow (analyst+)."""
    run = await AIService(session).run_campaign_plan(
        organization_id=organization_id,
        actor_user_id=current_user.id,
        business=business,
    )
    return AgentRunDetailOut.model_validate(run)


@router.post("/optimize", response_model=AgentRunDetailOut, status_code=status.HTTP_201_CREATED)
async def run_optimization(
    organization_id: uuid.UUID,
    body: OptimizeRequest,
    current_user: CurrentUser,
    membership: CurrentMembership,
    session: DbSession,
    meta: RequestMetadata,
) -> AgentRunDetailOut:
    """Run the optimization workflow (analyst+). Auto-execution requires admin+."""
    if role_rank(membership.role) < role_rank(OrgRole.ANALYST):
        raise ForbiddenError("This action requires at least the 'analyst' role.")
    if body.auto_execute and role_rank(membership.role) < role_rank(OrgRole.ADMIN):
        raise ForbiddenError("Autonomous execution requires at least the 'admin' role.")

    run = await AIService(session).run_optimization(
        organization_id=organization_id,
        actor_user_id=current_user.id,
        customer_id=body.customer_id,
        date_range=body.date_range,
        auto_execute=body.auto_execute,
        meta=meta,
    )
    return AgentRunDetailOut.model_validate(run)


@router.get("/runs", response_model=list[AgentRunOut])
async def list_runs(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    pagination: PaginationParams,
) -> list[AgentRunOut]:
    """List AI runs for the organization (any member)."""
    runs = await AIService(session).list_runs(
        organization_id, offset=pagination.offset, limit=pagination.limit
    )
    return [AgentRunOut.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AgentRunDetailOut)
async def get_run(
    organization_id: uuid.UUID,
    run_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
) -> AgentRunDetailOut:
    """Fetch a run with its full decision log (any member)."""
    run = await AIService(session).get_run(run_id, organization_id)
    if run is None:
        raise NotFoundError("Run not found.")
    return AgentRunDetailOut.model_validate(run)


@router.get("/memory/{namespace}")
async def list_memory(
    organization_id: uuid.UUID,
    namespace: str,
    membership: CurrentMembership,
    session: DbSession,
) -> list[dict]:
    """List durable agent memory entries in a namespace (any member)."""
    entries = await AIService(session).list_memory(organization_id, namespace)
    return [
        {"key": e.key, "value": e.value, "updated_at": e.updated_at.isoformat()} for e in entries
    ]
