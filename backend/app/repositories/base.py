"""Generic async repository implementing the repository pattern.

Concrete repositories subclass :class:`BaseRepository`, binding a specific
model. All database access flows through this layer, keeping services free of
raw SQLAlchemy and making data access independently testable.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base, SoftDeleteMixin

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Async CRUD operations for a single model type."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    @property
    def _supports_soft_delete(self) -> bool:
        return issubclass(self.model, SoftDeleteMixin)

    def _apply_active_filter(self, stmt: Any) -> Any:
        """Exclude soft-deleted rows unless the model has no soft-delete."""
        if self._supports_soft_delete:
            return stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    async def get(self, id_: uuid.UUID, *, include_deleted: bool = False) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id_)  # type: ignore[attr-defined]
        if not include_deleted:
            stmt = self._apply_active_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by(self, **filters: Any) -> ModelType | None:
        stmt = self._apply_active_filter(select(self.model).filter_by(**filters))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        order_by: Any | None = None,
        **filters: Any,
    ) -> list[ModelType]:
        stmt = self._apply_active_filter(select(self.model).filter_by(**filters))
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        stmt = self._apply_active_filter(
            select(func.count()).select_from(self.model).filter_by(**filters)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def create(self, **values: Any) -> ModelType:
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **values: Any) -> ModelType:
        for key, value in values.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType, *, hard: bool = False) -> None:
        """Soft-delete by default; hard-delete when requested or unsupported."""
        if self._supports_soft_delete and not hard:
            instance.deleted_at = func.now()  # type: ignore[attr-defined]
            await self.session.flush()
        else:
            await self.session.delete(instance)
            await self.session.flush()
