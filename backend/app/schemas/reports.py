"""Performance report schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: str
    date: date
    summary: str
    totals: dict = Field(default_factory=dict)
    created_at: datetime


class GenerateReportRequest(BaseModel):
    customer_id: str = Field(min_length=1)
