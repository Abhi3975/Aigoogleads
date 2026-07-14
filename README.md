# AI Ads Agent

> Autonomous AI marketing agent that plans, launches, monitors, and optimizes
> Google Ads campaigns end-to-end — within user-configured safety limits.

Production-grade SaaS. A user connects Google Ads, enters business info, sets a
budget and goals; a multi-agent AI system then researches, builds, launches, and
continuously optimizes campaigns — explaining every decision and staying within
configurable safety limits.

Full-stack and tested: **85 backend tests** (verified against PostgreSQL) and a
**21-route Next.js app**.

## Tech stack

| Layer        | Technology                                                        |
| ------------ | ----------------------------------------------------------------- |
| Frontend     | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, React Query |
| Backend      | FastAPI, Python 3.12, SQLAlchemy 2 (async), Alembic, Pydantic v2   |
| Database     | PostgreSQL                                                         |
| Cache/Broker | Redis                                                             |
| Jobs         | Celery (worker + beat)                                             |
| AI           | LangGraph, LangChain, OpenAI-compatible provider abstraction       |
| Integrations | Google Ads API, Google OAuth                                       |
| Infra        | Docker, Docker Compose, Nginx, GitHub Actions                      |

## Features

**Accounts & tenancy** — email/password + **Google OAuth** login, JWT with
refresh rotation & reuse detection, **password reset**, profile, multi-tenant
organizations, **5-role RBAC** (owner/admin/manager/analyst/viewer), team member
management.

**Google Ads** — OAuth connection with **encrypted tokens at rest**, account
sync, campaign/metrics reads, and mutations (create campaign, budget, pause/enable).

**Autonomous AI** — a supervisor coordinating specialized agents (strategy,
keyword research, ad copy, analytics, recommendation, execution) over an
OpenAI-compatible provider abstraction, with structured outputs, tool-calling,
persistent **memory + learning insights**, and full **decision/reasoning logs**.

**Campaign creation** — onboarding → website analysis → strategy → keywords → ad
copy → validated blueprint → one-click execution to Google Ads, with per-action
execution logs and rollback.

**Optimization engine** — Celery + Beat loop (metrics → analyze → recommend →
**Safety Decision Engine** → execute → audit), configurable per-org policy.

**SaaS** — usage metering + **plan limits** (free/starter/growth/enterprise)
enforced on AI actions, billing status/plan management, **API keys** for
programmatic access, notifications, performance reports, analytics dashboards.

**Ops** — rate limiting, security headers, request-id logging, `/health` +
`/ready` probes, GitHub Actions **CI + security scanning**, Docker Compose,
**Kubernetes manifests**.

## Application (frontend routes)

| Route | Purpose |
| --- | --- |
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/auth/callback` | Auth (incl. Google OAuth) |
| `/dashboard` | Overview, performance KPIs, recent AI activity |
| `/onboarding` | 6-step business onboarding wizard |
| `/campaigns`, `/campaigns/[id]` | Blueprints list + strategy preview / launch / status |
| `/analytics` | KPI cards + spend/conversion charts + campaign table |
| `/reports` | Generate & view daily performance reports |
| `/optimization` | Run the loop, safety-policy controls, decision history |
| `/insights` | AI Brain — ranked learnings |
| `/runs/[id]` | Per-agent decision log for an AI run |
| `/team`, `/billing`, `/settings`, `/profile` | Members/RBAC, plan/usage, integrations, account |

## Repository layout

```
Aigoogleads/
├── backend/            FastAPI service (API, services, repositories, agents, worker)
├── frontend/           Next.js application
├── nginx/              Reverse-proxy config
├── docs/               Architecture, ER, deployment & dev guides
├── docker-compose.yml  Full local stack
├── Makefile            Developer task runner
└── .env.example        Root environment template
```

## Quick start (Docker)

```bash
cp .env.example .env          # then edit secrets
make up                       # build & start the full stack
# API    → http://localhost:8000/docs
# Web    → http://localhost:3000
# Proxy  → http://localhost (nginx)
```

## Local development (without Docker)

```bash
make env                      # create .env files
make backend-install && make backend-run     # FastAPI on :8000
make frontend-install && make frontend-run    # Next.js on :3000
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — design & per-milestone plan
- [`docs/GOOGLE_ADS.md`](docs/GOOGLE_ADS.md) — Google Ads integration & verification
- [`docs/CAMPAIGN_CREATION.md`](docs/CAMPAIGN_CREATION.md) — autonomous campaign creation flow
- [`docs/OPTIMIZATION.md`](docs/OPTIMIZATION.md) — autonomous optimization engine (Celery + safety)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — dev + production deployment, env vars, security, monitoring

## Testing

```bash
cd backend  && uv run pytest        # 85 tests (needs PostgreSQL + Redis)
cd frontend && pnpm typecheck && pnpm lint && pnpm build
```

CI runs both on every PR (`.github/workflows/ci.yml`), plus secret/dependency
scanning (`.github/workflows/security.yml`).

## Development conventions

- **Backend**: Ruff (lint+format) + mypy (strict) + pytest. `make backend-lint`.
- **Frontend**: ESLint + Prettier + tsc. `make frontend-lint`.
- **Commits**: work is delivered milestone-by-milestone; each milestone is
  self-contained and extends the codebase (never regenerated).

## License

MIT — see [LICENSE](LICENSE).
