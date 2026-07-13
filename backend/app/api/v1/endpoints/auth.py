"""Authentication endpoints: register, login, refresh, logout, Google sign-in."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Query, Response, status

from app.api.deps import CurrentUser, DbSession, RequestMetadata
from app.core.config import settings
from app.core.exceptions import UnauthorizedError, ValidationError
from app.integrations.google_oauth import GoogleOAuthClient
from app.schemas.auth import (
    AuthResponse,
    GoogleAuthURL,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
OAUTH_STATE_COOKIE = "oauth_state"
_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=_COOKIE_PATH)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    session: DbSession,
    meta: RequestMetadata,
    response: Response,
) -> AuthResponse:
    """Create a password-based account and a default workspace, then log in."""
    user, tokens = await AuthService(session).register(
        email=data.email, password=data.password, full_name=data.full_name, meta=meta
    )
    _set_refresh_cookie(response, tokens.refresh_token)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/login", response_model=TokenPair)
async def login(
    data: LoginRequest,
    session: DbSession,
    meta: RequestMetadata,
    response: Response,
) -> TokenPair:
    """Authenticate with email + password; returns access + refresh tokens."""
    tokens = await AuthService(session).login(email=data.email, password=data.password, meta=meta)
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: DbSession,
    meta: RequestMetadata,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> TokenPair:
    """Rotate a refresh token (with reuse detection) and mint a new pair."""
    token = body.refresh_token or refresh_cookie
    if not token:
        raise ValidationError("A refresh token is required.")
    tokens = await AuthService(session).refresh(refresh_token=token, meta=meta)
    _set_refresh_cookie(response, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    session: DbSession,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> Response:
    """Revoke the current refresh token and clear the session cookie."""
    token = body.refresh_token or refresh_cookie
    await AuthService(session).logout(refresh_token=token)
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    """Return the currently authenticated user."""
    return UserOut.model_validate(current_user)


# --------------------------------------------------------------------------
# Google passwordless sign-in
# --------------------------------------------------------------------------
@router.get("/google/login", response_model=GoogleAuthURL)
async def google_login(response: Response) -> GoogleAuthURL:
    """Return the Google authorization URL and set a CSRF state cookie."""
    client = GoogleOAuthClient()
    if not client.is_configured:
        raise ValidationError("Google sign-in is not configured on this server.")

    from app.core.security import generate_state_token

    state = generate_state_token()
    url = client.build_authorization_url(state=state)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=_COOKIE_PATH,
    )
    return GoogleAuthURL(authorization_url=url, state=state)


@router.get("/google/callback", response_model=AuthResponse)
async def google_callback(
    session: DbSession,
    meta: RequestMetadata,
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    state_cookie: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE),
) -> AuthResponse:
    """Handle Google's redirect: verify state, exchange code, sign the user in."""
    if not state_cookie or state_cookie != state:
        raise UnauthorizedError("Invalid OAuth state.", error_code="invalid_oauth_state")

    client = GoogleOAuthClient()
    token_data = await client.exchange_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise UnauthorizedError("Google did not return an access token.")
    userinfo = await client.fetch_userinfo(access_token)

    user, tokens = await AuthService(session).authenticate_google(userinfo=userinfo, meta=meta)
    response.delete_cookie(OAUTH_STATE_COOKIE, path=_COOKIE_PATH)
    _set_refresh_cookie(response, tokens.refresh_token)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)
