"""User profile service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def update_profile(
        self, user: User, *, full_name: str | None = None, avatar_url: str | None = None
    ) -> User:
        values: dict[str, object] = {}
        if full_name is not None:
            values["full_name"] = full_name
        if avatar_url is not None:
            values["avatar_url"] = avatar_url
        if values:
            user = await self.users.update(user, **values)
            await self.session.commit()
            await self.session.refresh(user)
        return user
