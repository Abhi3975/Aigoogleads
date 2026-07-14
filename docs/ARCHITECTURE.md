# Architecture

## Overview

AI Ads Agent is a two-tier SaaS: a **Next.js** frontend and a **FastAPI**
backend, fronted by **Nginx**, backed by **PostgreSQL** and **Redis**, with
**Celery** running background jobs and the **LangGraph** multi-agent system.

```
                         ┌──────────────┐
              HTTPS       │    Nginx     │  reverse proxy / TLS
   Browser ───────────▶  │  (:80/:443)  │
                         └──────┬───────┘
                    /api/*      │        /*
             ┌───────────────┐  │  ┌───────────────┐
             │   FastAPI     │◀─┴─▶│   Next.js     │
             │  (backend)    │     │  (frontend)   │
             └───┬───────┬───┘     └───────────────┘
                 │       │
        ┌────────▼──┐  ┌─▼────────┐        ┌──────────────┐
        │ PostgreSQL│  │  Redis   │◀──────▶│ Celery worker│
        └───────────┘  └──────────┘  broker│  + beat      │
                                            └──────┬───────┘
                                                   │ invokes
                                            ┌──────▼───────┐
                                            │  LangGraph   │
                                            │ agent system │
                                            └──────┬───────┘
                                                   │
                                            ┌──────▼───────┐
                                            │ Google Ads   │
                                            │     API      │
                                            └──────────────┘
```

## Backend layering

Strict, one-directional dependency flow:

```
api (routers)  →  services (business logic)  →  repositories (data access)  →  models (ORM)
        │                     │
        └── schemas (Pydantic, request/response contracts)
```

- **api/** — thin HTTP routers; validation, auth dependencies, status codes.
- **services/** — orchestration and business rules; transaction boundaries.
- **repositories/** — all database access; pure data operations, unit-testable.
- **models/** — SQLAlchemy ORM entities.
- **schemas/** — Pydantic v2 models at the API boundary (never leak ORM objects).
- **integrations/** — Google Ads / OAuth clients, isolated behind interfaces.
- **agents/** — LangGraph supervisor + specialized agents.
- **worker/** — Celery app and scheduled/async tasks.
- **core/** — config, logging, security, exceptions (cross-cutting).

## Key decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Repo shape | Monorepo, two images | Shared history/CI; independent deploy & scale |
| API style | Async FastAPI + async SQLAlchemy | High concurrency; non-blocking I/O |
| Google Ads SDK (sync) | Runs in Celery / threadpool | Never blocks the async event loop |
| Config | Pydantic Settings, env-only | 12-factor; fail-fast validation |
| Errors | `AppError` hierarchy + global handlers | Consistent JSON envelopes, no stack leaks |
| Secrets at rest | Fernet-encrypted OAuth tokens | Compromised DB ≠ compromised Google accounts |
| Auth | Google OAuth + JWT (short) + refresh rotation | Stateless API, revocable sessions |
| AI provider | OpenAI-compatible abstraction | Swap providers without touching agent logic |
| Dep mgmt | `uv` (backend) · `pnpm` (frontend) | Fast, reproducible, lockfile-based |

## Build milestones (all delivered)

1. ✅ **M1 — Foundation & scaffolding**: monorepo, Docker, env, lint/format,
   dependency management, FastAPI health service, Next.js foundation.
2. ✅ **M2 — Database & core models**: schema, async SQLAlchemy models, Alembic,
   repository base, soft deletes, indexes.
3. ✅ **M3 — Auth & RBAC**: Google OAuth, JWT + refresh rotation, organizations,
   team members, 5-role RBAC, encrypted token storage.
4. ✅ **M4 — Google Ads integration**: API client, campaign/keyword/RSA CRUD,
   budget/status mutations, metrics, connection lifecycle.
5. ✅ **M5 — AI multi-agent system**: 9 specialized agents + Supervisor,
   structured outputs, tool calling, memory, reasoning/execution logs.
6. ✅ **M6 — Autonomous campaign creation** + **M6b optimization engine**: full
   onboarding→execution flow; Celery/Beat loop with the Safety Decision Engine.
7. ✅ **M7 — Frontend application**: 21 routes — dashboards, wizard, campaigns,
   analytics, reports, optimization, AI insights, run logs, team, billing,
   settings, profile.
8. ✅ **M8 — DevOps, security & docs**: rate limiting, security headers,
   request-id logging, `/health` + `/ready`, GitHub Actions CI + security scans,
   Docker + Kubernetes, docs.
9. ✅ **M9–M11 — SaaS layer**: AI learning insights, usage metering + plan
   limits, API keys, industry templates.

## Security posture (summary)

OAuth best practices, JWT rotation, encrypted sensitive tokens, rate limiting,
strict input validation (Pydantic/Zod), SQL-injection safety (parameterized
ORM), CORS allow-listing, security headers at the proxy, and audit logging.
Detailed in `docs/` as later milestones land.
