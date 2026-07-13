# AI Ads Agent

> Autonomous AI marketing agent that plans, launches, monitors, and optimizes
> Google Ads campaigns end-to-end — within user-configured safety limits.

Production-grade SaaS. A user connects Google Ads, enters business info, sets a
budget and goals; a LangGraph multi-agent system then researches, builds,
launches, and continuously optimizes campaigns, explaining every action.

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

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for design details and the
per-milestone build plan.

## Development conventions

- **Backend**: Ruff (lint+format) + mypy (strict) + pytest. `make backend-lint`.
- **Frontend**: ESLint + Prettier + tsc. `make frontend-lint`.
- **Commits**: work is delivered milestone-by-milestone; each milestone is
  self-contained and extends the codebase (never regenerated).

## License

MIT — see [LICENSE](LICENSE).
