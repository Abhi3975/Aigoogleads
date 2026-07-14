"""API key schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class APIKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str] = Field(default_factory=list)
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class APIKeyCreatedOut(APIKeyOut):
    # The full secret is returned exactly once, at creation.
    key: str


class APIKeyIdentity(BaseModel):
    organization_id: uuid.UUID
    name: str
    scopes: list[str] = Field(default_factory=list)
