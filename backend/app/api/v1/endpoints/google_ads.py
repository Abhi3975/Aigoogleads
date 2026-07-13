"""Google Ads integration endpoints.

Two routers:
- ``router``          — organization-scoped (RBAC via path organization_id)
- ``callback_router`` — the fixed OAuth redirect target (org derived from the
                        signed ``state`` value)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Cookie, Depends, Query, Response, status

from app.api.deps import CurrentMembership, CurrentUser, DbSession, RequestMetadata, require_role
from app.core.config import settings
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.security import create_signed_state, generate_state_token, verify_signed_state
from app.integrations.google_ads.oauth import ADS_SCOPE, GoogleAdsOAuthClient
from app.models.enums import OrgRole, role_rank
from app.models.organization import OrganizationMembership
from app.repositories.organization import MembershipRepository
from app.schemas.google_ads import (
    CampaignMetricsOut,
    CampaignOut,
    CreateCampaignRequest,
    CreateCampaignResult,
    GoogleAdsAccountOut,
    GoogleAdsAuthURL,
    GoogleAdsConnectionOut,
)
from app.services.google_ads import GoogleAdsService

router = APIRouter(prefix="/organizations/{organization_id}/google-ads", tags=["google-ads"])
callback_router = APIRouter(prefix="/integrations/google-ads", tags=["google-ads"])

STATE_COOKIE = "google_ads_state"
_COOKIE_PATH = f"{settings.API_V1_PREFIX}/integrations/google-ads"


def _connection_out(connection: object, accounts_count: int) -> GoogleAdsConnectionOut:
    return GoogleAdsConnectionOut(
        id=connection.id,  # type: ignore[attr-defined]
        organization_id=connection.organization_id,  # type: ignore[attr-defined]
        status=connection.status,  # type: ignore[attr-defined]
        login_customer_id=connection.login_customer_id,  # type: ignore[attr-defined]
        last_synced_at=connection.last_synced_at,  # type: ignore[attr-defined]
        accounts_count=accounts_count,
    )


# --------------------------------------------------------------------------
# Connection lifecycle
# --------------------------------------------------------------------------
@router.post("/connect", response_model=GoogleAdsAuthURL)
async def connect(
    organization_id: uuid.UUID,
    current_user: CurrentUser,
    response: Response,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> GoogleAdsAuthURL:
    """Begin the Google Ads OAuth flow (admin+). Returns the authorization URL."""
    client = GoogleAdsOAuthClient()
    if not client.is_configured:
        raise ValidationError(
            "Google Ads is not configured on this server "
            "(client id/secret and developer token are required)."
        )
    nonce = generate_state_token()
    state = create_signed_state(
        {"org": str(organization_id), "uid": str(current_user.id), "nonce": nonce}
    )
    url = client.build_authorization_url(state=state)
    response.set_cookie(
        STATE_COOKIE,
        nonce,
        max_age=600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=_COOKIE_PATH,
    )
    return GoogleAdsAuthURL(authorization_url=url, state=state)


@router.get("/connection", response_model=GoogleAdsConnectionOut | None)
async def get_connection(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> GoogleAdsConnectionOut | None:
    """Return the organization's Google Ads connection status (any member)."""
    service = GoogleAdsService(session)
    connection = await service.connections.get_active_for_org(organization_id)
    if connection is None:
        return None
    accounts = await service.list_accounts(organization_id)
    return _connection_out(connection, len(accounts))


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    organization_id: uuid.UUID,
    session: DbSession,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> None:
    """Revoke the organization's Google Ads connection (admin+)."""
    await GoogleAdsService(session).disconnect(organization_id)


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
@router.post("/accounts/sync", response_model=list[GoogleAdsAccountOut])
async def sync_accounts(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> list[GoogleAdsAccountOut]:
    """Fetch accessible customer accounts from Google and store them."""
    accounts = await GoogleAdsService(session).sync_accounts(organization_id)
    return [GoogleAdsAccountOut.model_validate(a) for a in accounts]


@router.get("/accounts", response_model=list[GoogleAdsAccountOut])
async def list_accounts(
    organization_id: uuid.UUID, membership: CurrentMembership, session: DbSession
) -> list[GoogleAdsAccountOut]:
    """List the organization's linked Google Ads accounts."""
    accounts = await GoogleAdsService(session).list_accounts(organization_id)
    return [GoogleAdsAccountOut.model_validate(a) for a in accounts]


# --------------------------------------------------------------------------
# Campaigns & metrics
# --------------------------------------------------------------------------
@router.get("/accounts/{customer_id}/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    organization_id: uuid.UUID,
    customer_id: str,
    membership: CurrentMembership,
    session: DbSession,
) -> list[CampaignOut]:
    """Read campaigns for a customer account (live)."""
    return await GoogleAdsService(session).list_campaigns(organization_id, customer_id)


@router.get("/accounts/{customer_id}/campaigns/metrics", response_model=list[CampaignMetricsOut])
async def campaign_metrics(
    organization_id: uuid.UUID,
    customer_id: str,
    membership: CurrentMembership,
    session: DbSession,
    date_range: str = Query("LAST_30_DAYS", description="Google Ads predefined date range"),
) -> list[CampaignMetricsOut]:
    """Read campaign performance metrics for a date range (live)."""
    return await GoogleAdsService(session).get_campaign_metrics(
        organization_id, customer_id, date_range
    )


@router.post(
    "/accounts/{customer_id}/campaigns",
    response_model=CreateCampaignResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    organization_id: uuid.UUID,
    customer_id: str,
    data: CreateCampaignRequest,
    current_user: CurrentUser,
    session: DbSession,
    meta: RequestMetadata,
    membership: OrganizationMembership = Depends(require_role(OrgRole.ADMIN)),
) -> CreateCampaignResult:
    """Create a (paused by default) Search campaign in the account (admin+)."""
    return await GoogleAdsService(session).create_campaign(
        organization_id=organization_id,
        customer_id=customer_id,
        data=data,
        actor_user_id=current_user.id,
        meta=meta,
    )


# --------------------------------------------------------------------------
# OAuth callback (fixed redirect target)
# --------------------------------------------------------------------------
@callback_router.get("/callback", response_model=GoogleAdsConnectionOut)
async def google_ads_callback(
    session: DbSession,
    meta: RequestMetadata,
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    state_cookie: str | None = Cookie(default=None, alias=STATE_COOKIE),
) -> GoogleAdsConnectionOut:
    """Handle Google's redirect: verify state, store tokens, sync accounts."""
    payload = verify_signed_state(state)
    if not state_cookie or state_cookie != payload.get("nonce"):
        raise UnauthorizedError("Invalid OAuth state.", error_code="invalid_oauth_state")

    organization_id = uuid.UUID(payload["org"])
    actor_id = uuid.UUID(payload["uid"])

    # Re-verify the authorizer is still an admin of the organization.
    membership = await MembershipRepository(session).get_membership(organization_id, actor_id)
    if membership is None or role_rank(membership.role) < role_rank(OrgRole.ADMIN):
        raise UnauthorizedError("Not authorized to connect this organization.")

    client = GoogleAdsOAuthClient()
    token_data = await client.exchange_code(code)
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValidationError(
            "Google did not return a refresh token. Revoke prior access and retry "
            "so the consent screen is shown."
        )

    service = GoogleAdsService(session)
    connection = await service.store_connection(
        organization_id=organization_id,
        authorized_by_user_id=actor_id,
        refresh_token=refresh_token,
        scopes=token_data.get("scope", ADS_SCOPE),
        login_customer_id=settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID or None,
        meta=meta,
    )

    # Best-effort account sync; connection is saved even if this fails.
    accounts_count = 0
    try:
        accounts = await service.sync_accounts(organization_id)
        accounts_count = len(accounts)
    except Exception as exc:  # pragma: no cover - depends on live API
        from app.core.logging import get_logger

        get_logger(__name__).warning("google_ads_initial_sync_failed", error=str(exc))

    response.delete_cookie(STATE_COOKIE, path=_COOKIE_PATH)
    return _connection_out(connection, accounts_count)
