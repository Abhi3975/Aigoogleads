"""Autonomous campaign-creation orchestrator.

Owns the end-to-end workflow: onboarding persistence, the AI planning pipeline
(website analysis -> strategy -> keywords -> ad copy -> blueprint), and safe
execution to Google Ads with retries, per-action logging, and safety controls.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import tenacity
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.campaign_creation import (
    AdCreativeAgent,
    KeywordPlannerAgent,
    StrategyArchitectAgent,
    WebsiteAnalysisAgent,
)
from app.agents.context import RunContext
from app.agents.llm.provider import get_provider
from app.core.config import settings
from app.core.context import RequestMeta
from app.core.exceptions import ConflictError, ExternalServiceError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.integrations.website import fetch_website_content
from app.models.agent import AgentRun
from app.models.campaign import (
    AudienceProfile,
    BudgetConfiguration,
    BusinessProfile,
    CampaignBlueprint,
    CampaignExecutionLog,
    ProductInformation,
)
from app.repositories.agent import AgentRunRepository
from app.repositories.campaign import (
    BusinessProfileRepository,
    CampaignBlueprintRepository,
    CampaignExecutionLogRepository,
    WebsiteAnalysisRepository,
)
from app.schemas.campaign import (
    OnboardingRequest,
    PlanRequest,
)
from app.services.audit import AuditService
from app.services.campaign_assembler import assemble_blueprint
from app.services.google_ads import GoogleAdsService

logger = get_logger(__name__)


class CampaignCreationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = BusinessProfileRepository(session)
        self.analyses = WebsiteAnalysisRepository(session)
        self.blueprints = CampaignBlueprintRepository(session)
        self.exec_logs = CampaignExecutionLogRepository(session)
        self.runs = AgentRunRepository(session)
        self.ads = GoogleAdsService(session)
        self.audit = AuditService(session)

    # ---------------------------------------------------------------- onboarding
    async def save_onboarding(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        data: OnboardingRequest,
    ) -> BusinessProfile:
        # Soft-delete any existing active profile (keep history).
        existing = await self.profiles.get_current(organization_id)
        if existing is not None:
            existing.deleted_at = datetime.now(UTC)

        profile = BusinessProfile(
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            business_name=data.business_name,
            description=data.description,
            industry=data.industry,
            website_url=data.website_url,
            product_service_description=data.product_service_description,
            usp=data.usp,
            location=data.location,
            target_countries=data.target_countries,
            target_cities=data.target_cities,
            languages=data.languages,
            goal=data.goal.value,
        )
        self.session.add(profile)
        await self.session.flush()

        self.session.add(
            BudgetConfiguration(
                business_profile_id=profile.id,
                daily_budget=data.budget.daily_budget,
                monthly_budget=data.budget.monthly_budget,
                currency=data.budget.currency.upper(),
                max_cpa=data.budget.max_cpa,
                target_roas=data.budget.target_roas,
            )
        )
        if data.audience is not None:
            a = data.audience
            self.session.add(
                AudienceProfile(
                    business_profile_id=profile.id,
                    age_min=a.age_min,
                    age_max=a.age_max,
                    gender=a.gender,
                    locations=a.locations,
                    interests=a.interests,
                    pain_points=a.pain_points,
                    existing_customer_profile=a.existing_customer_profile,
                )
            )
        for product in data.products:
            self.session.add(
                ProductInformation(
                    business_profile_id=profile.id,
                    name=product.name,
                    pricing=product.pricing,
                    features=product.features,
                    benefits=product.benefits,
                    landing_url=product.landing_url,
                )
            )

        await self.audit.record(
            "onboarding.save",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="business_profile",
            resource_id=str(profile.id),
        )
        await self.session.commit()
        reloaded = await self.profiles.get_with_children(profile.id)
        assert reloaded is not None
        return reloaded

    async def get_profile(self, organization_id: uuid.UUID) -> BusinessProfile | None:
        return await self.profiles.get_current(organization_id)

    # ------------------------------------------------------------------- planning
    async def run_plan(
        self, *, organization_id: uuid.UUID, actor_user_id: uuid.UUID | None, req: PlanRequest
    ) -> tuple[AgentRun, CampaignBlueprint]:
        profile = await self.profiles.get_current(organization_id)
        if profile is None:
            raise NotFoundError("Complete business onboarding before planning a campaign.")

        provider = get_provider()
        run = await self.runs.create(
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            workflow="campaign_creation",
            status="running",
            input={"business_profile_id": str(profile.id), "customer_id": req.customer_id},
            started_at=datetime.now(UTC),
        )
        await self.session.commit()

        ctx = RunContext(
            session=self.session,
            run=run,
            provider=provider,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        try:
            business_payload = _profile_payload(profile)

            website_analysis: dict[str, Any] | None = None
            if req.analyze_website and profile.website_url:
                website_analysis = await self._analyze_website(ctx, profile)

            strategy = await StrategyArchitectAgent().run(
                ctx,
                {
                    "business": business_payload,
                    "goal": profile.goal,
                    "budget": _budget_payload(profile.budget),
                    "audience": _audience_payload(profile.audience),
                    "website_analysis": website_analysis,
                },
            )
            keywords = await KeywordPlannerAgent().run(
                ctx, {"business": business_payload, "strategy": strategy.model_dump(mode="json")}
            )
            ad_creative = await AdCreativeAgent().run(
                ctx,
                {
                    "business": business_payload,
                    "strategy": strategy.model_dump(mode="json"),
                    "keywords": keywords.model_dump(mode="json"),
                },
            )

            daily_budget = _safe_daily_budget(strategy.recommended_daily_budget, profile.budget)
            structure = assemble_blueprint(
                strategy=strategy,
                keywords=keywords,
                ad_creative=ad_creative,
                daily_budget=daily_budget,
            )

            blueprint = await self.blueprints.create(
                organization_id=organization_id,
                business_profile_id=profile.id,
                created_by_user_id=actor_user_id,
                run_id=run.id,
                customer_id=req.customer_id,
                campaign_name=strategy.campaign_name,
                campaign_type=strategy.campaign_type.value,
                objective=strategy.objective,
                daily_budget=daily_budget,
                bidding_strategy=strategy.bidding_strategy,
                structure=structure.model_dump(mode="json"),
                status="draft",
            )

            run.output = {
                "blueprint_id": str(blueprint.id),
                "campaign_name": blueprint.campaign_name,
                "validation_warnings": structure.validation_warnings,
            }
            run.status = "completed"
            run.total_tokens = ctx.total_tokens
            run.completed_at = datetime.now(UTC)
            await self.session.commit()
        except Exception as exc:
            logger.warning("campaign_plan_failed", error=str(exc))
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = datetime.now(UTC)
            await self.session.commit()
            raise

        run = await self.runs.get_with_steps(run.id, organization_id)  # type: ignore[assignment]
        blueprint = await self.blueprints.get_for_org(blueprint.id, organization_id)  # type: ignore[assignment]
        assert run is not None and blueprint is not None
        return run, blueprint

    async def _analyze_website(self, ctx: RunContext, profile: BusinessProfile) -> dict[str, Any]:
        content = await fetch_website_content(profile.website_url or "")
        output = await WebsiteAnalysisAgent().run(
            ctx,
            {
                "url": content.url,
                "title": content.title,
                "description": content.description,
                "content": content.text,
            },
        )
        analysis = await self.analyses.create(
            organization_id=ctx.organization_id,
            business_profile_id=profile.id,
            url=content.url,
            business_summary=output.business_summary,
            products=output.products,
            services=output.services,
            target_customer=output.target_customer,
            keywords=output.keywords,
            selling_points=output.selling_points,
            recommended_strategy=output.recommended_strategy,
            raw=output.model_dump(mode="json"),
        )
        _ = analysis
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------ execution
    async def execute_blueprint(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        blueprint_id: uuid.UUID,
        customer_id: str,
        start_paused: bool = True,
        meta: RequestMeta | None = None,
    ) -> CampaignBlueprint:
        blueprint = await self.blueprints.get_for_org(blueprint_id, organization_id)
        if blueprint is None:
            raise NotFoundError("Blueprint not found.")
        if blueprint.status in {"created", "executing"}:
            raise ConflictError(f"Blueprint is already '{blueprint.status}'.")

        # --- Safety controls -------------------------------------------------
        self._validate_budget(float(blueprint.daily_budget))
        duplicate = await self.blueprints.find_created_duplicate(
            organization_id, customer_id, blueprint.campaign_name
        )
        if duplicate is not None:
            raise ConflictError(
                "A campaign with this name already exists in this account.",
                error_code="duplicate_campaign",
            )

        blueprint.customer_id = customer_id
        blueprint.status = "executing"
        await self.session.commit()

        try:
            result = await self._build_with_retry(
                organization_id, customer_id, blueprint.structure, start_paused
            )
        except Exception as exc:
            blueprint.status = "failed"
            await self.exec_logs.create(
                blueprint_id=blueprint.id,
                organization_id=organization_id,
                sequence=1,
                action="build_campaign",
                status="failed",
                error=str(exc),
            )
            await self.audit.record(
                "campaign.execute_failed",
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                resource_type="campaign_blueprint",
                resource_id=str(blueprint.id),
                context={"error": str(exc)},
                meta=meta,
            )
            await self.session.commit()
            raise

        for i, step in enumerate(result.get("steps", []), start=1):
            await self.exec_logs.create(
                blueprint_id=blueprint.id,
                organization_id=organization_id,
                sequence=i,
                action=step.get("action", "unknown"),
                resource_type=step.get("resource_type"),
                google_resource_id=step.get("google_resource_id"),
                status=step.get("status", "success"),
                error=step.get("error"),
            )
        blueprint.google_campaign_id = result.get("campaign_id")
        blueprint.status = "created"
        await self.audit.record(
            "campaign.created",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="campaign",
            resource_id=str(result.get("campaign_id")),
            context={"customer_id": customer_id, "blueprint_id": str(blueprint.id)},
            meta=meta,
        )
        await self.session.commit()

        reloaded = await self.blueprints.get_for_org(blueprint.id, organization_id)
        assert reloaded is not None
        return reloaded

    async def _build_with_retry(
        self, organization_id: uuid.UUID, customer_id: str, structure: dict, paused: bool
    ) -> dict:
        async for attempt in tenacity.AsyncRetrying(
            retry=tenacity.retry_if_exception_type(ExternalServiceError),
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        ):
            with attempt:
                return await self.ads.build_full_campaign(
                    organization_id=organization_id,
                    customer_id=customer_id,
                    structure=structure,
                    paused=paused,
                )
        raise ExternalServiceError("Campaign build failed after retries.")  # pragma: no cover

    def _validate_budget(self, daily_budget: float) -> None:
        if daily_budget <= 0:
            raise ValidationError("Daily budget must be positive.")
        if daily_budget > settings.SAFETY_MAX_DAILY_BUDGET:
            raise ValidationError(
                f"Daily budget {daily_budget} exceeds the safety cap "
                f"({settings.SAFETY_MAX_DAILY_BUDGET}).",
                error_code="budget_exceeds_safety_cap",
            )

    # ------------------------------------------------------------------- reads
    async def list_blueprints(
        self, organization_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CampaignBlueprint]:
        return await self.blueprints.list_for_org(organization_id, offset=offset, limit=limit)

    async def get_blueprint(
        self, blueprint_id: uuid.UUID, organization_id: uuid.UUID
    ) -> CampaignBlueprint | None:
        return await self.blueprints.get_for_org(blueprint_id, organization_id)

    async def list_execution_logs(self, blueprint_id: uuid.UUID) -> list[CampaignExecutionLog]:
        return await self.exec_logs.list_for_blueprint(blueprint_id)


# -- Payload / safety helpers ----------------------------------------------
def _profile_payload(profile: BusinessProfile) -> dict[str, Any]:
    return {
        "business_name": profile.business_name,
        "description": profile.description,
        "industry": profile.industry,
        "website_url": profile.website_url,
        "product_service_description": profile.product_service_description,
        "usp": profile.usp,
        "location": profile.location,
        "target_countries": profile.target_countries,
        "target_cities": profile.target_cities,
        "languages": profile.languages,
        "goal": profile.goal,
    }


def _budget_payload(budget: BudgetConfiguration | None) -> dict[str, Any] | None:
    if budget is None:
        return None
    return {
        "daily_budget": float(budget.daily_budget),
        "monthly_budget": float(budget.monthly_budget),
        "currency": budget.currency,
        "max_cpa": float(budget.max_cpa) if budget.max_cpa is not None else None,
        "target_roas": float(budget.target_roas) if budget.target_roas is not None else None,
    }


def _audience_payload(audience: AudienceProfile | None) -> dict[str, Any] | None:
    if audience is None:
        return None
    return {
        "age_min": audience.age_min,
        "age_max": audience.age_max,
        "gender": audience.gender,
        "locations": audience.locations,
        "interests": audience.interests,
        "pain_points": audience.pain_points,
        "existing_customer_profile": audience.existing_customer_profile,
    }


def _safe_daily_budget(recommended: float, budget: BudgetConfiguration | None) -> float:
    """Clamp the AI-recommended budget to the user's budget and the safety cap."""
    candidates = [float(recommended), settings.SAFETY_MAX_DAILY_BUDGET]
    if budget is not None:
        candidates.append(float(budget.daily_budget))
    return max(1.0, min(candidates))
