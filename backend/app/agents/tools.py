"""Tool interfaces exposing the Google Ads API to agents.

``TOOL_SPECS`` describes each tool in OpenAI function-calling format (name,
description, JSON-schema parameters) so it can be advertised to an LLM for tool
calling. ``GoogleAdsToolset`` binds those tools to a concrete service, org, and
customer account and executes them, returning JSON-serialisable results.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.core.context import RequestMeta
from app.services.google_ads import GoogleAdsService


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _obj(**props: Any) -> dict[str, Any]:
    required = [k for k, v in props.items() if v.pop("_required", False)]
    return {"type": "object", "properties": props, "required": required}


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        "get_campaigns",
        "List campaigns for the current customer account.",
        _obj(),
    ),
    ToolSpec(
        "get_metrics",
        "Read campaign performance metrics for a predefined date range.",
        _obj(date_range={"type": "string", "_required": True}),
    ),
    ToolSpec(
        "create_campaign",
        "Create a new (paused) Search campaign with a daily budget.",
        _obj(
            name={"type": "string", "_required": True},
            daily_budget={"type": "number", "_required": True},
        ),
    ),
    ToolSpec(
        "pause_campaign",
        "Pause a campaign by id.",
        _obj(campaign_id={"type": "string", "_required": True}),
    ),
    ToolSpec(
        "enable_campaign",
        "Enable a campaign by id.",
        _obj(campaign_id={"type": "string", "_required": True}),
    ),
    ToolSpec(
        "update_budget",
        "Update a campaign's daily budget.",
        _obj(
            campaign_id={"type": "string", "_required": True},
            daily_budget={"type": "number", "_required": True},
        ),
    ),
]


class GoogleAdsToolset:
    """Executable tools bound to a service + organization + customer account."""

    def __init__(
        self,
        *,
        service: GoogleAdsService,
        organization_id: uuid.UUID,
        customer_id: str,
        actor_user_id: uuid.UUID | None = None,
        meta: RequestMeta | None = None,
    ) -> None:
        self.service = service
        self.organization_id = organization_id
        self.customer_id = customer_id
        self.actor_user_id = actor_user_id
        self.meta = meta

    @staticmethod
    def specs() -> list[dict[str, Any]]:
        return [spec.to_openai() for spec in TOOL_SPECS]

    async def get_campaigns(self) -> list[dict[str, Any]]:
        campaigns = await self.service.list_campaigns(self.organization_id, self.customer_id)
        return [c.model_dump(mode="json") for c in campaigns]

    async def get_metrics(self, date_range: str) -> list[dict[str, Any]]:
        metrics = await self.service.get_campaign_metrics(
            self.organization_id, self.customer_id, date_range
        )
        return [m.model_dump(mode="json") for m in metrics]

    async def create_campaign(self, *, name: str, daily_budget: float) -> dict[str, Any]:
        from app.schemas.google_ads import CreateCampaignRequest

        result = await self.service.create_campaign(
            organization_id=self.organization_id,
            customer_id=self.customer_id,
            data=CreateCampaignRequest(name=name, daily_budget=daily_budget),
            actor_user_id=self.actor_user_id,
            meta=self.meta,
        )
        return result.model_dump(mode="json")

    async def pause_campaign(self, *, campaign_id: str) -> dict[str, Any]:
        return await self.service.set_campaign_status(
            organization_id=self.organization_id,
            customer_id=self.customer_id,
            campaign_id=campaign_id,
            status="PAUSED",
            actor_user_id=self.actor_user_id,
            meta=self.meta,
        )

    async def enable_campaign(self, *, campaign_id: str) -> dict[str, Any]:
        return await self.service.set_campaign_status(
            organization_id=self.organization_id,
            customer_id=self.customer_id,
            campaign_id=campaign_id,
            status="ENABLED",
            actor_user_id=self.actor_user_id,
            meta=self.meta,
        )

    async def update_budget(self, *, campaign_id: str, daily_budget: float) -> dict[str, Any]:
        return await self.service.update_campaign_budget(
            organization_id=self.organization_id,
            customer_id=self.customer_id,
            campaign_id=campaign_id,
            daily_budget=daily_budget,
            actor_user_id=self.actor_user_id,
            meta=self.meta,
        )
