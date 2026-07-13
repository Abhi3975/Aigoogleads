"""User profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserOut, UserProfileUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_profile(current_user: CurrentUser) -> UserOut:
    """Return the authenticated user's profile."""
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_profile(
    data: UserProfileUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> UserOut:
    """Update the authenticated user's profile."""
    user = await UserService(session).update_profile(
        current_user, full_name=data.full_name, avatar_url=data.avatar_url
    )
    return UserOut.model_validate(user)
