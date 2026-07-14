"""Campaign-creation schemas: onboarding, website analysis, plan, blueprint."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agents import AgentRunDetailOut, MatchType


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------
class MarketingGoal(str, enum.Enum):
    GENERATE_LEADS = "generate_leads"
    INCREASE_SALES = "increase_sales"
    WEBSITE_TRAFFIC = "website_traffic"
    APP_INSTALLS = "app_installs"
    BRAND_AWARENESS = "brand_awareness"
    LOCAL_STORE_VISITS = "local_store_visits"


class CampaignType(str, enum.Enum):
    SEARCH = "SEARCH"
    DISPLAY = "DISPLAY"
    PERFORMANCE_MAX = "PERFORMANCE_MAX"
    SHOPPING = "SHOPPING"


class KeywordIntent(str, enum.Enum):
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"
    INFORMATIONAL = "informational"


# --------------------------------------------------------------------------
# Onboarding — inputs
# --------------------------------------------------------------------------
class BudgetIn(BaseModel):
    daily_budget: float = Field(gt=0)
    monthly_budget: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    max_cpa: float | None = Field(default=None, gt=0)
    target_roas: float | None = Field(default=None, gt=0)


class AudienceIn(BaseModel):
    age_min: int | None = Field(default=None, ge=13, le=100)
    age_max: int | None = Field(default=None, ge=13, le=100)
    gender: str | None = None
    locations: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    existing_customer_profile: str | None = None


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    pricing: str | None = None
    features: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    landing_url: str | None = None


class OnboardingRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=8000)
    industry: str = Field(min_length=1, max_length=160)
    website_url: str | None = None
    product_service_description: str | None = None
    usp: str | None = None
    location: str | None = None
    target_countries: list[str] = Field(default_factory=list)
    target_cities: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    goal: MarketingGoal
    budget: BudgetIn
    audience: AudienceIn | None = None
    products: list[ProductIn] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Onboarding — outputs
# --------------------------------------------------------------------------
class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    daily_budget: float
    monthly_budget: float
    currency: str
    max_cpa: float | None = None
    target_roas: float | None = None


class AudienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    age_min: int | None = None
    age_max: int | None = None
    gender: str | None = None
    locations: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    existing_customer_profile: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    pricing: str | None = None
    features: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    landing_url: str | None = None


class BusinessProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    description: str
    industry: str
    website_url: str | None = None
    product_service_description: str | None = None
    usp: str | None = None
    location: str | None = None
    target_countries: list[str] = Field(default_factory=list)
    target_cities: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    goal: str
    status: str
    created_at: datetime
    budget: BudgetOut | None = None
    audience: AudienceOut | None = None
    products: list[ProductOut] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Website analysis
# --------------------------------------------------------------------------
class WebsiteAnalysisOutput(BaseModel):
    business_summary: str
    products: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    target_customer: str = ""
    keywords: list[str] = Field(default_factory=list)
    selling_points: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    landing_page_quality: str | None = None
    recommended_strategy: str = ""
    reasoning: str = ""


class WebsiteAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    business_summary: str
    products: list[str]
    services: list[str]
    target_customer: str
    keywords: list[str]
    selling_points: list[str]
    recommended_strategy: str
    status: str
    created_at: datetime


# --------------------------------------------------------------------------
# Strategy / keyword / ad-copy structured outputs
# --------------------------------------------------------------------------
class AdGroupPlan(BaseModel):
    name: str
    theme: str
    suggested_keyword_count: int = 10


class CampaignStrategyPlan(BaseModel):
    campaign_name: str
    campaign_type: CampaignType = CampaignType.SEARCH
    objective: str
    recommended_daily_budget: float
    bidding_strategy: str
    location_targeting: list[str] = Field(default_factory=list)
    audience_targeting: str = ""
    ad_groups: list[AdGroupPlan] = Field(default_factory=list)
    reasoning: str


class KeywordSpec(BaseModel):
    text: str
    match_type: MatchType = MatchType.PHRASE
    intent: KeywordIntent = KeywordIntent.COMMERCIAL


class AdGroupKeywords(BaseModel):
    ad_group_name: str
    keywords: list[KeywordSpec] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)


class KeywordPlanOutput(BaseModel):
    groups: list[AdGroupKeywords] = Field(default_factory=list)
    shared_negative_keywords: list[str] = Field(default_factory=list)
    reasoning: str


class Sitelink(BaseModel):
    text: str
    url: str | None = None
    description: str | None = None


class AdExtensions(BaseModel):
    sitelinks: list[Sitelink] = Field(default_factory=list)
    callouts: list[str] = Field(default_factory=list)


class RSACreative(BaseModel):
    ad_group_name: str
    headlines: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    final_url: str
    path1: str | None = None
    path2: str | None = None


class AdCreativeOutput(BaseModel):
    ads: list[RSACreative] = Field(default_factory=list)
    extensions: AdExtensions = Field(default_factory=AdExtensions)
    reasoning: str


# --------------------------------------------------------------------------
# Assembled blueprint structure (persisted in CampaignBlueprint.structure)
# --------------------------------------------------------------------------
class BlueprintAdGroup(BaseModel):
    name: str
    theme: str
    keywords: list[KeywordSpec] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    ad: RSACreative | None = None


class BlueprintStructure(BaseModel):
    campaign_name: str
    campaign_type: CampaignType
    objective: str
    daily_budget: float
    bidding_strategy: str
    location_targeting: list[str] = Field(default_factory=list)
    audience_targeting: str = ""
    ad_groups: list[BlueprintAdGroup] = Field(default_factory=list)
    shared_negative_keywords: list[str] = Field(default_factory=list)
    extensions: AdExtensions = Field(default_factory=AdExtensions)
    validation_warnings: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Blueprint / execution read models & requests
# --------------------------------------------------------------------------
class CampaignBlueprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_name: str
    campaign_type: str
    objective: str
    daily_budget: float
    bidding_strategy: str
    status: str
    customer_id: str | None = None
    google_campaign_id: str | None = None
    structure: dict = Field(default_factory=dict)
    created_at: datetime


class ExecutionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    action: str
    resource_type: str | None = None
    google_resource_id: str | None = None
    status: str
    error: str | None = None
    created_at: datetime


class PlanRequest(BaseModel):
    customer_id: str | None = None
    analyze_website: bool = True


class ExecuteRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    start_paused: bool = True


class CampaignPlanResponse(BaseModel):
    run: AgentRunDetailOut
    blueprint: CampaignBlueprintOut
