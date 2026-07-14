"""Performance report endpoints."""

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
from app.schemas.reports import DailyReportOut, GenerateReportRequest
from app.services.reports import ReportsService

router = APIRouter(prefix="/organizations/{organization_id}/reports", tags=["reports"])


@router.get("", response_model=list[DailyReportOut])
async def list_reports(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    pagination: PaginationParams,
) -> list[DailyReportOut]:
    """List generated performance reports (any member)."""
    reports = await ReportsService(session).list(
        organization_id, offset=pagination.offset, limit=pagination.limit
    )
    return [DailyReportOut.model_validate(r) for r in reports]


@router.post("/generate", response_model=DailyReportOut, status_code=status.HTTP_201_CREATED)
async def generate_report(
    organization_id: uuid.UUID,
    body: GenerateReportRequest,
    current_user: CurrentUser,
    session: DbSession,
    meta: RequestMetadata,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ANALYST)),
) -> DailyReportOut:
    """Generate (or refresh) today's performance report for an account (analyst+)."""
    report = await ReportsService(session).generate(
        organization_id=organization_id,
        customer_id=body.customer_id,
        actor_user_id=current_user.id,
        meta=meta,
    )
    return DailyReportOut.model_validate(report)
