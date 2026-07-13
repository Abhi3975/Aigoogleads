# AI Ads Agent — Backend

FastAPI service powering the autonomous AI Google Ads platform.

## Layout

```
app/
├── main.py              # Application factory + ASGI entrypoint
├── core/                # Config, logging, security, exceptions (cross-cutting)
├── api/                 # HTTP layer — versioned routers (thin)
├── models/             # SQLAlchemy ORM models          (added in M2)
├── schemas/            # Pydantic request/response models (added in M2)
├── repositories/       # Data-access layer               (added in M2)
├── services/           # Business logic                  (added in M3+)
├── integrations/       # Google Ads / OAuth clients      (added in M4)
├── agents/             # LangGraph multi-agent system    (added in M5)
└── worker/             # Celery app + tasks              (added in M6)
```

## Local development

```bash
uv sync --all-extras          # install deps (needs `uv`)
cp .env.example .env          # configure
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

## Quality

```bash
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy app               # type-check
uv run pytest                 # tests
```
