"""Organization & membership service."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import generate_state_token
from app.models.enums import OrgRole, role_rank
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.repositories.organization import MembershipRepository, OrganizationRepository
from app.repositories.user import UserRepository


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "org"


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orgs = OrganizationRepository(session)
        self.members = MembershipRepository(session)
        self.users = UserRepository(session)

    async def _unique_slug(self, name: str) -> str:
        base = _slugify(name)
        candidate = base
        while await self.orgs.get_by_slug(candidate) is not None:
            candidate = f"{base}-{generate_state_token()[:6].lower()}"
        return candidate

    async def create_organization(
        self, *, name: str, owner: User, flush_only: bool = False
    ) -> Organization:
        """Create an organization and make ``owner`` its OWNER."""
        slug = await self._unique_slug(name)
        org = await self.orgs.create(name=name, slug=slug, owner_id=owner.id)
        await self.members.create(organization_id=org.id, user_id=owner.id, role=OrgRole.OWNER)
        if not flush_only:
            await self.session.commit()
            await self.session.refresh(org)
        return org

    async def create_default_organization(self, owner: User) -> Organization:
        """A personal workspace created on signup (flushed, not committed)."""
        label = (owner.full_name or owner.email.split("@")[0]).strip()
        return await self.create_organization(
            name=f"{label}'s Workspace", owner=owner, flush_only=True
        )

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        return await self.orgs.list_for_user(user_id)

    async def get_membership_or_403(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMembership:
        membership = await self.members.get_membership(organization_id, user_id)
        if membership is None:
            raise ForbiddenError("You are not a member of this organization.")
        return membership

    async def list_members(self, organization_id: uuid.UUID) -> list[OrganizationMembership]:
        return await self.members.list_members(organization_id)

    async def add_member(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
        role: OrgRole,
        actor: OrganizationMembership,
    ) -> OrganizationMembership:
        self._require_min_role(actor, OrgRole.ADMIN)
        if role_rank(role) >= role_rank(actor.role):
            raise ForbiddenError("Cannot assign a role equal to or above your own.")

        user = await self.users.get_by_email(email)
        if user is None:
            raise NotFoundError("No user with that email exists.")
        if await self.members.get_membership(organization_id, user.id) is not None:
            raise ConflictError("User is already a member of this organization.")

        membership = await self.members.create(
            organization_id=organization_id, user_id=user.id, role=role
        )
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def update_member_role(
        self,
        *,
        organization_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: OrgRole,
        actor: OrganizationMembership,
    ) -> OrganizationMembership:
        self._require_min_role(actor, OrgRole.ADMIN)
        membership = await self.members.get_membership(organization_id, target_user_id)
        if membership is None:
            raise NotFoundError("Membership not found.")
        if membership.role == OrgRole.OWNER:
            raise ForbiddenError("The organization owner's role cannot be changed.")
        if role_rank(role) >= role_rank(actor.role):
            raise ForbiddenError("Cannot assign a role equal to or above your own.")

        membership = await self.members.update(membership, role=role)
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def remove_member(
        self,
        *,
        organization_id: uuid.UUID,
        target_user_id: uuid.UUID,
        actor: OrganizationMembership,
    ) -> None:
        self._require_min_role(actor, OrgRole.ADMIN)
        membership = await self.members.get_membership(organization_id, target_user_id)
        if membership is None:
            raise NotFoundError("Membership not found.")
        if membership.role == OrgRole.OWNER:
            raise ForbiddenError("The organization owner cannot be removed.")
        await self.members.delete(membership, hard=True)
        await self.session.commit()

    @staticmethod
    def _require_min_role(membership: OrganizationMembership, minimum: OrgRole) -> None:
        if role_rank(membership.role) < role_rank(minimum):
            raise ForbiddenError("Insufficient role for this action.")
