"""Organization & membership endpoints (RBAC-gated)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentMembership, CurrentUser, DbSession, require_role
from app.models.enums import OrgRole
from app.models.organization import OrganizationMembership
from app.schemas.organization import (
    MemberAdd,
    MemberOut,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationOut,
    OrganizationWithRole,
)
from app.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _member_out(membership: OrganizationMembership) -> MemberOut:
    return MemberOut(
        user_id=membership.user_id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.get("", response_model=list[OrganizationWithRole])
async def list_my_organizations(
    current_user: CurrentUser, session: DbSession
) -> list[OrganizationWithRole]:
    """List organizations the current user belongs to, with their role."""
    from app.repositories.organization import MembershipRepository

    memberships = await MembershipRepository(session).list_for_user(current_user.id)
    return [
        OrganizationWithRole(
            id=m.organization.id,
            name=m.organization.name,
            slug=m.organization.slug,
            plan=m.organization.plan,
            created_at=m.organization.created_at,
            role=m.role,
        )
        for m in memberships
    ]


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate, current_user: CurrentUser, session: DbSession
) -> OrganizationOut:
    """Create a new organization; the creator becomes its owner."""
    org = await OrganizationService(session).create_organization(name=data.name, owner=current_user)
    return OrganizationOut.model_validate(org)


@router.get("/{organization_id}", response_model=OrganizationOut)
async def get_organization(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> OrganizationOut:
    """Fetch an organization the current user is a member of."""
    org = await OrganizationService(session).orgs.get(organization_id)
    assert org is not None  # membership implies existence
    return OrganizationOut.model_validate(org)


@router.get("/{organization_id}/members", response_model=list[MemberOut])
async def list_members(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> list[MemberOut]:
    """List members of an organization (any member may view)."""
    members = await OrganizationService(session).list_members(organization_id)
    return [_member_out(m) for m in members]


@router.post(
    "/{organization_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    organization_id: uuid.UUID,
    data: MemberAdd,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> MemberOut:
    """Add an existing user to the organization (admin+)."""
    created = await OrganizationService(session).add_member(
        organization_id=organization_id, email=data.email, role=data.role, actor=membership
    )
    # Reload with user relationship for the response.
    from app.repositories.organization import MembershipRepository

    members = await MembershipRepository(session).list_members(organization_id)
    target = next(m for m in members if m.id == created.id)
    return _member_out(target)


@router.patch("/{organization_id}/members/{target_user_id}", response_model=MemberOut)
async def update_member_role(
    organization_id: uuid.UUID,
    target_user_id: uuid.UUID,
    data: MemberRoleUpdate,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> MemberOut:
    """Change a member's role (admin+)."""
    await OrganizationService(session).update_member_role(
        organization_id=organization_id,
        target_user_id=target_user_id,
        role=data.role,
        actor=membership,
    )
    from app.repositories.organization import MembershipRepository

    members = await MembershipRepository(session).list_members(organization_id)
    target = next(m for m in members if m.user_id == target_user_id)
    return _member_out(target)


@router.delete(
    "/{organization_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    organization_id: uuid.UUID,
    target_user_id: uuid.UUID,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> None:
    """Remove a member from the organization (admin+)."""
    await OrganizationService(session).remove_member(
        organization_id=organization_id, target_user_id=target_user_id, actor=membership
    )
