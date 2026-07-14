"""Campaign creation endpoints: onboarding, AI planning, and execution."""

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
from app.core.exceptions import NotFoundError
from app.models.enums import OrgRole
from app.models.organization import OrganizationMembership
from app.schemas.agents import AgentRunDetailOut
from app.schemas.campaign import (
    BusinessProfileOut,
    CampaignBlueprintOut,
    CampaignPlanResponse,
    ExecuteRequest,
    ExecutionLogOut,
    OnboardingRequest,
    PlanRequest,
)
from app.services.campaign_creation import CampaignCreationService

router = APIRouter(prefix="/organizations/{organization_id}/campaigns", tags=["campaigns"])


# ------------------------------------------------------------------- onboarding
@router.post("/onboarding", response_model=BusinessProfileOut, status_code=status.HTTP_201_CREATED)
async def save_onboarding(
    organization_id: uuid.UUID,
    data: OnboardingRequest,
    current_user: CurrentUser,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ANALYST)),
) -> BusinessProfileOut:
    """Save the business onboarding information (analyst+)."""
    profile = await CampaignCreationService(session).save_onboarding(
        organization_id=organization_id, actor_user_id=current_user.id, data=data
    )
    return BusinessProfileOut.model_validate(profile)


@router.get("/onboarding", response_model=BusinessProfileOut | None)
async def get_onboarding(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> BusinessProfileOut | None:
    """Fetch the current business profile (any member)."""
    profile = await CampaignCreationService(session).get_profile(organization_id)
    return BusinessProfileOut.model_validate(profile) if profile is not None else None


# --------------------------------------------------------------------- planning
@router.post("/plan", response_model=CampaignPlanResponse, status_code=status.HTTP_201_CREATED)
async def plan_campaign(
    organization_id: uuid.UUID,
    body: PlanRequest,
    current_user: CurrentUser,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ANALYST)),
) -> CampaignPlanResponse:
    """Run the AI campaign-creation workflow and produce a draft blueprint (analyst+)."""
    run, blueprint = await CampaignCreationService(session).run_plan(
        organization_id=organization_id, actor_user_id=current_user.id, req=body
    )
    return CampaignPlanResponse(
        run=AgentRunDetailOut.model_validate(run),
        blueprint=CampaignBlueprintOut.model_validate(blueprint),
    )


# -------------------------------------------------------------------- execution
@router.post(
    "/{blueprint_id}/execute",
    response_model=CampaignBlueprintOut,
    status_code=status.HTTP_201_CREATED,
)
async def execute_campaign(
    organization_id: uuid.UUID,
    blueprint_id: uuid.UUID,
    body: ExecuteRequest,
    current_user: CurrentUser,
    session: DbSession,
    meta: RequestMetadata,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> CampaignBlueprintOut:
    """Create the campaign in Google Ads from a blueprint (admin+)."""
    blueprint = await CampaignCreationService(session).execute_blueprint(
        organization_id=organization_id,
        actor_user_id=current_user.id,
        blueprint_id=blueprint_id,
        customer_id=body.customer_id,
        start_paused=body.start_paused,
        meta=meta,
    )
    return CampaignBlueprintOut.model_validate(blueprint)


# ------------------------------------------------------------------------ reads
@router.get("", response_model=list[CampaignBlueprintOut])
async def list_blueprints(
    organization_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
    pagination: PaginationParams,
) -> list[CampaignBlueprintOut]:
    """List campaign blueprints for the organization (any member)."""
    blueprints = await CampaignCreationService(session).list_blueprints(
        organization_id, offset=pagination.offset, limit=pagination.limit
    )
    return [CampaignBlueprintOut.model_validate(b) for b in blueprints]


@router.get("/{blueprint_id}", response_model=CampaignBlueprintOut)
async def get_blueprint(
    organization_id: uuid.UUID,
    blueprint_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
) -> CampaignBlueprintOut:
    """Fetch a single blueprint (any member)."""
    blueprint = await CampaignCreationService(session).get_blueprint(blueprint_id, organization_id)
    if blueprint is None:
        raise NotFoundError("Blueprint not found.")
    return CampaignBlueprintOut.model_validate(blueprint)


@router.get("/{blueprint_id}/execution-logs", response_model=list[ExecutionLogOut])
async def list_execution_logs(
    organization_id: uuid.UUID,
    blueprint_id: uuid.UUID,
    membership: CurrentMembership,
    session: DbSession,
) -> list[ExecutionLogOut]:
    """List per-action execution logs for a blueprint (any member)."""
    service = CampaignCreationService(session)
    blueprint = await service.get_blueprint(blueprint_id, organization_id)
    if blueprint is None:
        raise NotFoundError("Blueprint not found.")
    logs = await service.list_execution_logs(blueprint_id)
    return [ExecutionLogOut.model_validate(log) for log in logs]
