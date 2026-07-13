"""FastAPI dependency-injection providers.

Centralizes reusable request dependencies: DB session, pagination, request
metadata, current-user authentication, and RBAC role gating.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestMeta
from app.core.db import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.enums import OrgRole, role_rank
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.repositories.user import UserRepository

# Per-request async database session.
DbSession = Annotated[AsyncSession, Depends(get_session)]


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------
@dataclass(slots=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Items per page")] = 20,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


PaginationParams = Annotated[Pagination, Depends(get_pagination)]


# --------------------------------------------------------------------------
# Request metadata
# --------------------------------------------------------------------------
def get_request_meta(request: Request) -> RequestMeta:
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    return RequestMeta(ip_address=client_ip, user_agent=request.headers.get("user-agent"))


RequestMetadata = Annotated[RequestMeta, Depends(get_request_meta)]


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=False, description="JWT access token")


async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Not authenticated.", error_code="not_authenticated")

    payload = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject.", error_code="invalid_token") from exc

    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.", error_code="inactive_user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# --------------------------------------------------------------------------
# RBAC — organization membership + role gating
# --------------------------------------------------------------------------
async def get_org_membership(
    session: DbSession,
    user: CurrentUser,
    organization_id: Annotated[uuid.UUID, Path(description="Organization id")],
) -> OrganizationMembership:
    from app.repositories.organization import MembershipRepository

    membership = await MembershipRepository(session).get_membership(organization_id, user.id)
    if membership is None:
        raise ForbiddenError("You are not a member of this organization.")
    return membership


CurrentMembership = Annotated[OrganizationMembership, Depends(get_org_membership)]


def require_role(
    minimum: OrgRole,
) -> Callable[[OrganizationMembership], Awaitable[OrganizationMembership]]:
    """Dependency factory enforcing a minimum organization role."""

    async def _dependency(membership: CurrentMembership) -> OrganizationMembership:
        if role_rank(membership.role) < role_rank(minimum):
            raise ForbiddenError(f"This action requires at least the '{minimum.value}' role.")
        return membership

    return _dependency
