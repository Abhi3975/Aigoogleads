"""FastAPI dependency-injection providers.

Centralizes reusable request dependencies (DB session, pagination) so routers
stay declarative. Auth/RBAC dependencies are added in Milestone 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session

# Per-request async database session.
DbSession = Annotated[AsyncSession, Depends(get_session)]


@dataclass(slots=True)
class Pagination:
    """Normalized pagination parameters with computed offset."""

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
    """Provide validated pagination parameters."""
    return Pagination(page=page, page_size=page_size)


PaginationParams = Annotated[Pagination, Depends(get_pagination)]
