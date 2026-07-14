"""Industry template endpoints (reference data)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.exceptions import NotFoundError
from app.schemas.industry import IndustryTemplate
from app.services import industry_templates

router = APIRouter(prefix="/industry-templates", tags=["industry"])


@router.get("", response_model=list[IndustryTemplate])
async def list_industry_templates() -> list[IndustryTemplate]:
    """List all industry marketing templates."""
    return industry_templates.list_templates()


@router.get("/{industry}", response_model=IndustryTemplate)
async def get_industry_template(industry: str) -> IndustryTemplate:
    """Fetch a single industry template by key (e.g. 'ecommerce')."""
    template = industry_templates.get_template(industry)
    if template is None:
        raise NotFoundError(f"No template for industry '{industry}'.")
    return template
