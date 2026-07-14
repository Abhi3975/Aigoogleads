"""Assembles specialist agent outputs into a validated campaign blueprint.

Pure functions (no I/O) so they are fully unit-testable. Enforces Google Ads
Responsive Search Ad limits: headlines <=30 chars (3-15), descriptions <=90
chars (2-4), de-duplicated.
"""

from __future__ import annotations

from app.schemas.campaign import (
    AdCreativeOutput,
    BlueprintAdGroup,
    BlueprintStructure,
    CampaignStrategyPlan,
    KeywordPlanOutput,
    RSACreative,
)

HEADLINE_MAX = 30
DESCRIPTION_MAX = 90
HEADLINES_MIN, HEADLINES_MAX = 3, 15
DESCRIPTIONS_MIN, DESCRIPTIONS_MAX = 2, 4


def _clean(items: list[str], *, max_len: int, max_count: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        text = raw.strip()
        if not text or len(text) > max_len:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max_count:
            break
    return out


def assemble_blueprint(
    *,
    strategy: CampaignStrategyPlan,
    keywords: KeywordPlanOutput,
    ad_creative: AdCreativeOutput,
    daily_budget: float,
) -> BlueprintStructure:
    kw_by_group = {g.ad_group_name: g for g in keywords.groups}
    ad_by_group = {a.ad_group_name: a for a in ad_creative.ads}
    warnings: list[str] = []
    ad_groups: list[BlueprintAdGroup] = []

    for group in strategy.ad_groups:
        kg = kw_by_group.get(group.name)
        raw_ad = ad_by_group.get(group.name)

        rsa: RSACreative | None = None
        if raw_ad is not None:
            headlines = _clean(raw_ad.headlines, max_len=HEADLINE_MAX, max_count=HEADLINES_MAX)
            descriptions = _clean(
                raw_ad.descriptions, max_len=DESCRIPTION_MAX, max_count=DESCRIPTIONS_MAX
            )
            if len(headlines) < HEADLINES_MIN:
                warnings.append(
                    f"Ad group '{group.name}': fewer than {HEADLINES_MIN} valid headlines."
                )
            if len(descriptions) < DESCRIPTIONS_MIN:
                warnings.append(
                    f"Ad group '{group.name}': fewer than {DESCRIPTIONS_MIN} valid descriptions."
                )
            rsa = RSACreative(
                ad_group_name=group.name,
                headlines=headlines,
                descriptions=descriptions,
                final_url=raw_ad.final_url,
                path1=raw_ad.path1,
                path2=raw_ad.path2,
            )
        else:
            warnings.append(f"Ad group '{group.name}': no ad copy generated.")

        if kg is None or not kg.keywords:
            warnings.append(f"Ad group '{group.name}': no keywords generated.")

        ad_groups.append(
            BlueprintAdGroup(
                name=group.name,
                theme=group.theme,
                keywords=kg.keywords if kg else [],
                negative_keywords=kg.negative_keywords if kg else [],
                ad=rsa,
            )
        )

    return BlueprintStructure(
        campaign_name=strategy.campaign_name,
        campaign_type=strategy.campaign_type,
        objective=strategy.objective,
        daily_budget=daily_budget,
        bidding_strategy=strategy.bidding_strategy,
        location_targeting=strategy.location_targeting,
        audience_targeting=strategy.audience_targeting,
        ad_groups=ad_groups,
        shared_negative_keywords=keywords.shared_negative_keywords,
        extensions=ad_creative.extensions,
        validation_warnings=warnings,
    )
