"""Authentication service: registration, login, token rotation, Google sign-in."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.context import RequestMeta
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair
from app.services.audit import AuditService
from app.services.organization import OrganizationService

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.orgs = OrganizationService(session)
        self.audit = AuditService(session)

    # -- Registration / login ---------------------------------------------
    async def register(
        self, *, email: str, password: str, full_name: str | None, meta: RequestMeta
    ) -> tuple[User, TokenPair]:
        email = email.lower()
        if await self.users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")

        user = await self.users.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_email_verified=False,
        )
        await self.orgs.create_default_organization(user)
        tokens = await self._issue_token_pair(user, meta)
        await self.audit.record(
            "user.register",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            meta=meta,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user, tokens

    async def login(self, *, email: str, password: str, meta: RequestMeta) -> TokenPair:
        user = await self.users.get_by_email(email.lower())
        # Constant-ish behavior: always verify to reduce user-enumeration timing.
        if user is None or user.hashed_password is None:
            raise UnauthorizedError("Invalid email or password.", error_code="invalid_credentials")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.", error_code="invalid_credentials")
        if not user.is_active:
            raise ForbiddenError("This account is disabled.")

        tokens = await self._issue_token_pair(user, meta)
        user.last_login_at = datetime.now(UTC)
        await self.audit.record(
            "user.login",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            meta=meta,
        )
        await self.session.commit()
        return tokens

    # -- Google passwordless sign-in --------------------------------------
    async def authenticate_google(
        self, *, userinfo: dict[str, Any], meta: RequestMeta
    ) -> tuple[User, TokenPair]:
        sub = str(userinfo["sub"])
        email = str(userinfo["email"]).lower()

        user = await self.users.get_by_google_sub(sub)
        created = False
        if user is None:
            user = await self.users.get_by_email(email)
            if user is not None:
                user.google_sub = sub  # link existing account
            else:
                user = await self.users.create(
                    email=email,
                    google_sub=sub,
                    full_name=userinfo.get("name"),
                    avatar_url=userinfo.get("picture"),
                    is_email_verified=bool(userinfo.get("email_verified", True)),
                )
                await self.orgs.create_default_organization(user)
                created = True

        if not user.is_active:
            raise ForbiddenError("This account is disabled.")

        user.last_login_at = datetime.now(UTC)
        if userinfo.get("picture") and not user.avatar_url:
            user.avatar_url = userinfo["picture"]

        tokens = await self._issue_token_pair(user, meta)
        await self.audit.record(
            "user.login_google" if not created else "user.register_google",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            meta=meta,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user, tokens

    # -- Refresh rotation --------------------------------------------------
    async def refresh(self, *, refresh_token: str, meta: RequestMeta) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        record = await self.refresh_tokens.get_by_jti(payload["jti"])

        if record is None:
            raise UnauthorizedError("Unknown refresh token.", error_code="invalid_token")

        if record.revoked_at is not None:
            # A revoked token is being replayed => probable theft. Kill the family.
            await self.refresh_tokens.revoke_family(record.family_id)
            await self.session.commit()
            logger.warning("refresh_token_reuse_detected", family_id=record.family_id)
            raise UnauthorizedError(
                "Refresh token reuse detected; session revoked.",
                error_code="token_reuse_detected",
            )

        if record.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Refresh token expired.", error_code="token_expired")

        user = await self.users.get(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User is no longer active.", error_code="inactive_user")

        # Rotate within the same family, revoking the presented token.
        tokens, new_jti = await self._issue_token_pair(
            user, meta, family_id=record.family_id, return_jti=True
        )
        await self.refresh_tokens.revoke(record, replaced_by_jti=new_jti)
        await self.session.commit()
        return tokens

    async def logout(self, *, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except UnauthorizedError:
            return
        record = await self.refresh_tokens.get_by_jti(payload["jti"])
        if record is not None and record.revoked_at is None:
            await self.refresh_tokens.revoke(record)
            await self.session.commit()

    # -- Helpers -----------------------------------------------------------
    async def _issue_token_pair(
        self,
        user: User,
        meta: RequestMeta,
        *,
        family_id: str | None = None,
        return_jti: bool = False,
    ) -> Any:
        access = create_access_token(user.id)
        refresh, payload = create_refresh_token(user.id, family_id=family_id)
        await self.refresh_tokens.create(
            user_id=user.id,
            jti=payload["jti"],
            family_id=payload["fam"],
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
            user_agent=meta.user_agent,
            ip_address=meta.ip_address,
        )
        pair = TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        if return_jti:
            return pair, payload["jti"]
        return pair
