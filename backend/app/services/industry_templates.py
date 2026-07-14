"""Industry-specific marketing templates.

Curated strategy priors per industry that seed the AI campaign-creation flow
and give users a strong, vertical-aware starting point. Served as reference
data (no per-tenant state), and injectable into the strategy agent's context.
"""

from __future__ import annotations

from app.schemas.industry import IndustryTemplate

_TEMPLATES: dict[str, IndustryTemplate] = {
    "ecommerce": IndustryTemplate(
        industry="ecommerce",
        display_name="E-commerce / Retail",
        recommended_campaign_type="PERFORMANCE_MAX",
        objective="increase_sales",
        bidding_strategy="MAXIMIZE_CONVERSION_VALUE",
        keyword_themes=[
            "buy <product> online",
            "best <product>",
            "<product> deals",
            "<brand> store",
        ],
        ad_angles=["Free shipping", "Limited-time offer", "Bestseller", "Easy returns"],
        suggested_negative_keywords=["free", "diy", "used", "jobs", "wholesale"],
        budget_guidance="Start with Performance Max + a branded Search campaign; scale by ROAS.",
    ),
    "real_estate": IndustryTemplate(
        industry="real_estate",
        display_name="Real Estate",
        recommended_campaign_type="SEARCH",
        objective="generate_leads",
        bidding_strategy="MAXIMIZE_CONVERSIONS",
        keyword_themes=[
            "homes for sale in <city>",
            "<city> real estate agent",
            "apartments <city>",
        ],
        ad_angles=["Book a viewing", "New listings", "Local expert", "Free valuation"],
        suggested_negative_keywords=["rent", "jobs", "salary", "zillow", "free"],
        budget_guidance="Tight geo-targeting; lead-form extensions; focus high-intent terms.",
    ),
    "saas": IndustryTemplate(
        industry="saas",
        display_name="SaaS / B2B Software",
        recommended_campaign_type="SEARCH",
        objective="generate_leads",
        bidding_strategy="MAXIMIZE_CONVERSIONS",
        keyword_themes=[
            "<category> software",
            "best <category> tool",
            "<competitor> alternative",
            "<category> for teams",
        ],
        ad_angles=[
            "Start free trial",
            "Book a demo",
            "No credit card required",
            "Trusted by teams",
        ],
        suggested_negative_keywords=["free", "crack", "torrent", "jobs", "tutorial"],
        budget_guidance="High-intent + competitor terms; retarget trial signups; measure by CPA.",
    ),
    "education": IndustryTemplate(
        industry="education",
        display_name="Education / Online Courses",
        recommended_campaign_type="SEARCH",
        objective="generate_leads",
        bidding_strategy="MAXIMIZE_CONVERSIONS",
        keyword_themes=["<subject> course online", "learn <skill>", "<certification> training"],
        ad_angles=["Enroll today", "Certificate included", "Learn at your pace", "Career outcomes"],
        suggested_negative_keywords=["free", "pdf", "download", "jobs"],
        budget_guidance="Lead-gen with strong CTAs; seasonal peaks around enrollment windows.",
    ),
    "healthcare": IndustryTemplate(
        industry="healthcare",
        display_name="Healthcare / Clinics",
        recommended_campaign_type="SEARCH",
        objective="local_store_visits",
        bidding_strategy="MAXIMIZE_CONVERSIONS",
        keyword_themes=[
            "<specialty> near me",
            "book <service> appointment",
            "<condition> treatment <city>",
        ],
        ad_angles=[
            "Book an appointment",
            "Same-day availability",
            "Insurance accepted",
            "Trusted care",
        ],
        suggested_negative_keywords=["jobs", "salary", "free", "symptoms"],
        budget_guidance="Local intent + call/location extensions; follow healthcare ad policies.",
    ),
    "local_services": IndustryTemplate(
        industry="local_services",
        display_name="Local Services",
        recommended_campaign_type="SEARCH",
        objective="generate_leads",
        bidding_strategy="MAXIMIZE_CONVERSIONS",
        keyword_themes=[
            "<service> near me",
            "<service> in <city>",
            "emergency <service>",
            "affordable <service>",
        ],
        ad_angles=["Free quote", "Same-day service", "Licensed & insured", "5-star rated"],
        suggested_negative_keywords=["jobs", "diy", "free", "how to"],
        budget_guidance="Tight radius targeting; call-focused ads; bid up on emergency terms.",
    ),
}


def list_templates() -> list[IndustryTemplate]:
    return list(_TEMPLATES.values())


def get_template(industry: str) -> IndustryTemplate | None:
    return _TEMPLATES.get(industry.strip().lower().replace(" ", "_").replace("-", "_"))
