"""Shared / cross-cutting Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Liveness/readiness payload."""

    status: str = Field(examples=["ok"])
    service: str
    version: str
    environment: str


class Message(BaseModel):
    """Generic message envelope."""

    message: str


class PageMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class Page(BaseModel, Generic[T]):
    """Generic paginated response envelope."""

    items: list[T]
    meta: PageMeta


class Timestamped(BaseModel):
    """Mixin exposing audit timestamps on responses."""

    created_at: datetime
    updated_at: datetime
