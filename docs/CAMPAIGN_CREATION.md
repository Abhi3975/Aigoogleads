# Autonomous Campaign Creation

End-to-end feature: a user provides business information once, and the AI
Marketing Agent analyzes the business, designs a Google Ads campaign strategy,
generates assets, and creates the campaign via the Google Ads API — with safety
controls and full audit/execution logging.

## Data flow

```
Onboarding form  ──▶  BusinessProfile (+Budget, +Audience, +Products)
        │
        ▼   POST /campaigns/plan
  Website Analysis Agent ──▶ WebsiteAnalysis   (fetch site → structured intel)
        ▼
  Strategy Architect Agent ─▶ campaign type, budget, bidding, ad groups
        ▼
  Keyword Planner Agent ────▶ intent-grouped keywords + negatives
        ▼
  Ad Creative Agent ────────▶ RSAs (15 headlines / 4 descriptions) + extensions
        ▼
  Blueprint Assembler ──────▶ validates RSA limits, clamps budget → CampaignBlueprint (draft)
        │
        ▼   POST /campaigns/{id}/execute  (admin)
  Safety controls ──────────▶ budget cap · duplicate prevention · connection check
        ▼
  Campaign Builder (client.build_full_campaign, retried) ──▶ Google Ads API
        ▼
  CampaignExecutionLog per action ──▶ blueprint.status = created (or failed + rollback)
```

Every AI step is persisted as an `AgentStep` (reasoning + tokens) under an
`AgentRun`; every Google Ads write is persisted as a `CampaignExecutionLog`.

## New files

**Models** — `app/models/campaign.py`: `BusinessProfile`, `BudgetConfiguration`,
`AudienceProfile`, `ProductInformation`, `WebsiteAnalysis`, `CampaignBlueprint`,
`CampaignExecutionLog`.

**Schemas** — `app/schemas/campaign.py`: onboarding I/O, `WebsiteAnalysisOutput`,
`CampaignStrategyPlan`, `KeywordPlanOutput`, `AdCreativeOutput`,
`BlueprintStructure`, blueprint/execution read models, enums (`MarketingGoal`,
`CampaignType`, `KeywordIntent`).

**Agents** — `app/agents/campaign_creation.py`: `WebsiteAnalysisAgent`,
`StrategyArchitectAgent`, `KeywordPlannerAgent`, `AdCreativeAgent`.

**Integrations** — `app/integrations/website.py`: dependency-free website fetch
+ text extraction. `app/integrations/google_ads/client.py`: `build_full_campaign`
(budget → campaign → ad groups → keywords → negatives → RSA) with rollback.

**Services** — `app/services/campaign_assembler.py` (pure assembly + RSA
validation), `app/services/campaign_creation.py` (orchestrator: onboarding,
planning, execution, safety). `app/services/google_ads.py` gains
`build_full_campaign`.

**Repositories** — `app/repositories/campaign.py`.

**API** — `app/api/v1/endpoints/campaigns.py`.

**Tests** — `tests/test_campaign_creation.py` (assembler, onboarding, planning,
website analysis, execution, safety).

## API endpoints (all under `/api/v1`)

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/organizations/{org}/campaigns/onboarding` | analyst+ | Save business info, budget, audience, products |
| GET | `/organizations/{org}/campaigns/onboarding` | member | Current business profile |
| POST | `/organizations/{org}/campaigns/plan` | analyst+ | Run AI workflow → draft blueprint |
| POST | `/organizations/{org}/campaigns/{id}/execute` | admin+ | Create the campaign in Google Ads |
| GET | `/organizations/{org}/campaigns` | member | List blueprints |
| GET | `/organizations/{org}/campaigns/{id}` | member | Blueprint detail (+ structure) |
| GET | `/organizations/{org}/campaigns/{id}/execution-logs` | member | Per-action execution logs |

## Database changes

New tables: `business_profiles`, `budget_configurations`, `audience_profiles`,
`product_information`, `website_analyses`, `campaign_blueprints`,
`campaign_execution_logs`. Migration:
`alembic/versions/*_add_campaign_creation_tables.py`.

The `campaign_blueprints.structure` column (JSONB) stores an immutable snapshot
of the full plan (ad groups, keywords, negatives, ads, extensions) — the
source of truth for execution.

## Safety controls

- **Budget cap** — `SAFETY_MAX_DAILY_BUDGET` hard-limits any created campaign's
  daily budget; the AI recommendation is clamped to `min(recommended, user
  daily budget, cap)`.
- **Budget validation** — positive, within cap, checked again at execution.
- **Duplicate prevention** — refuses to create a campaign whose name already
  exists (status `created`) for the same account.
- **Connection check** — execution requires an active Google Ads connection and
  a linked account.
- **Retries** — the builder retries transient API errors (tenacity, 3 attempts).
- **Rollback** — on failure the partially-created campaign/budget are removed
  (best-effort) and the blueprint is marked `failed` with an execution log.
- **Audit + execution logs** — every save/plan/execute action is recorded.

## Verification

`tests/test_campaign_creation.py` verifies the whole flow with an injected fake
LLM provider and fake Google Ads client (real LLM/API need credentials): RSA
char-limit validation, onboarding CRUD, the 3-agent plan pipeline (4 with
website analysis), budget clamping, campaign creation with per-action logs,
duplicate prevention, connection requirement, and the budget safety cap.

> **Frontend** (onboarding wizard, strategy preview, creation-status pages) is
> delivered in the frontend milestone and consumes these endpoints.
