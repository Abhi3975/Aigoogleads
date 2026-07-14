"""Autonomous optimization endpoints: policy, manual run, and audit history."""

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
from app.models.enums import OrgRole
from app.models.organization import OrganizationMembership
from app.repositories.optimization import (
    OptimizationLogRepository,
    OptimizationPolicyRepository,
)
from app.schemas.optimization import (
    OptimizationLogOut,
    OptimizationPolicyOut,
    OptimizationPolicyUpdate,
    OptimizationRunRequest,
    OptimizationRunSummary,
)
from app.services.optimization_engine import OptimizationEngine

router = APIRouter(prefix="/organizations/{organization_id}/optimization", tags=["optimization"])


@router.get("/policy", response_model=OptimizationPolicyOut)
async def get_policy(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> OptimizationPolicyOut:
    """Fetch the organization's optimization safety policy (any member)."""
    policy = await OptimizationPolicyRepository(session).get_or_create(organization_id)
    return OptimizationPolicyOut.model_validate(policy)


@router.patch("/policy", response_model=OptimizationPolicyOut)
async def update_policy(
    organization_id: uuid.UUID,
    data: OptimizationPolicyUpdate,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> OptimizationPolicyOut:
    """Update optimization safety rules & autonomy toggles (admin+)."""
    repo = OptimizationPolicyRepository(session)
    policy = await repo.get_or_create(organization_id)
    updates = data.model_dump(exclude_none=True)
    if updates:
        await repo.update(policy, **updates)
        await session.commit()
    return OptimizationPolicyOut.model_validate(policy)


@router.get("/logs", response_model=list[OptimizationLogOut])
async def list_logs(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    pagination: PaginationParams,
) -> list[OptimizationLogOut]:
    """List the optimization audit trail (any member)."""
    logs = await OptimizationLogRepository(session).list_for_org(
        organization_id, offset=pagination.offset, limit=pagination.limit
    )
    return [OptimizationLogOut.model_validate(log) for log in logs]


@router.post("/run", response_model=OptimizationRunSummary, status_code=status.HTTP_201_CREATED)
async def run_optimization(
    organization_id: uuid.UUID,
    body: OptimizationRunRequest,
    current_user: CurrentUser,
    session: DbSession,
    meta: RequestMetadata,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> OptimizationRunSummary:
    """Manually trigger the optimization loop for an account (admin+)."""
    result = await OptimizationEngine(session).run(
        organization_id=organization_id,
        customer_id=body.customer_id,
        actor_user_id=current_user.id,
        date_range=body.date_range,
        auto_execute=body.auto_execute,
        meta=meta,
    )
    counts = result["counts"]
    logs = await OptimizationLogRepository(session).list_for_run(result["run_id"])
    return OptimizationRunSummary(
        run_id=result["run_id"],
        applied=counts.get("applied", 0),
        pending=counts.get("pending", 0),
        rejected=counts.get("rejected", 0),
        failed=counts.get("failed", 0),
        logs=[OptimizationLogOut.model_validate(log) for log in logs],
    )
