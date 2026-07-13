"""Organization & membership schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import OrgPlan, OrgRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: OrgPlan
    created_at: datetime


class OrganizationWithRole(OrganizationOut):
    """Organization plus the requesting user's role within it."""

    role: OrgRole


class MemberAdd(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.VIEWER


class MemberRoleUpdate(BaseModel):
    role: OrgRole


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: OrgRole
    created_at: datetime
