"""API key management + key-authenticated identity endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, status

from app.api.deps import CurrentMembership, CurrentUser, DbSession, require_role
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.models.enums import OrgRole
from app.models.organization import OrganizationMembership
from app.schemas.api_key import APIKeyCreate, APIKeyCreatedOut, APIKeyIdentity, APIKeyOut
from app.services.api_key import APIKeyService

router = APIRouter(prefix="/organizations/{organization_id}/api-keys", tags=["api-keys"])
key_router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=APIKeyCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    organization_id: uuid.UUID,
    data: APIKeyCreate,
    current_user: CurrentUser,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> APIKeyCreatedOut:
    """Create an API key (admin+). The secret is returned once, here only."""
    key, raw = await APIKeyService(session).create(
        organization_id=organization_id,
        name=data.name,
        actor_user_id=current_user.id,
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    return APIKeyCreatedOut(**APIKeyOut.model_validate(key).model_dump(), key=raw)


@router.get("", response_model=list[APIKeyOut])
async def list_api_keys(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> list[APIKeyOut]:
    """List API keys (metadata only; secrets are never returned) — any member."""
    keys = await APIKeyService(session).list(organization_id)
    return [APIKeyOut.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    organization_id: uuid.UUID,
    key_id: uuid.UUID,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> None:
    """Revoke an API key (admin+)."""
    if not await APIKeyService(session).revoke(organization_id, key_id):
        raise NotFoundError("API key not found.")


@key_router.get("/whoami", response_model=APIKeyIdentity)
async def api_key_whoami(
    session: DbSession,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> APIKeyIdentity:
    """Resolve the organization/context for a presented API key."""
    key = await APIKeyService(session).verify(x_api_key)
    if key is None:
        raise UnauthorizedError("Invalid or revoked API key.", error_code="invalid_api_key")
    return APIKeyIdentity(
        organization_id=key.organization_id, name=key.name, scopes=list(key.scopes)
    )
