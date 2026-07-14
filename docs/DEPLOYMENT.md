# Deployment Guide

## Local development

```bash
# 1. Environment
cp .env.example .env            # fill in secrets (see "Environment variables")
make env                        # creates backend/.env and frontend/.env.local

# 2a. Everything via Docker (recommended)
make up                         # postgres, redis, backend, worker, beat, frontend, nginx
docker compose exec backend alembic upgrade head

# 2b. Or run services directly
cd backend && uv sync --all-extras && uv run alembic upgrade head
uv run uvicorn app.main:app --reload                       # API :8000
uv run celery -A app.worker.celery_app worker -l INFO      # worker
uv run celery -A app.worker.celery_app beat -l INFO        # scheduler
cd frontend && pnpm install && pnpm dev                     # web :3000
```

- API docs: http://localhost:8000/docs · Web: http://localhost:3000 · Proxy: http://localhost

## Testing

```bash
cd backend && uv run ruff check . && uv run pytest      # lint + tests (needs postgres + redis)
cd frontend && pnpm lint && pnpm typecheck && pnpm build
```

CI (GitHub Actions) runs both on every PR: `.github/workflows/ci.yml`. Docker
images build (and publish to GHCR when permitted) on `main`:
`.github/workflows/docker.yml`.

## Production deployment (Docker Compose)

**Server requirements:** Linux host with Docker + Docker Compose, 2 vCPU / 4 GB
RAM minimum (more for AI workloads), ports 80/443 open.

```bash
git clone <repo> && cd Aigoogleads
cp .env.example .env            # set production secrets + ENVIRONMENT=production
make up
docker compose exec backend alembic upgrade head
```

Compose services: `postgres`, `redis`, `backend` (gunicorn/uvicorn), `worker`,
`beat`, `frontend` (Next.js standalone), `nginx` (reverse proxy). All have
health checks and restart policies.

### TLS / SSL

Terminate TLS at nginx. Obtain certificates (e.g. Let's Encrypt via certbot or a
load balancer) and mount them, then add an HTTPS server block that proxies to the
`backend`/`frontend` upstreams (mirror `nginx/conf.d/default.conf`) and redirects
`:80` → `:443`. Set `BACKEND_CORS_ORIGINS` and the OAuth redirect URIs to your
`https://` domain.

### Domain

Point an A/AAAA record at the host, set the domain in nginx `server_name`, and
update `GOOGLE_OAUTH_REDIRECT_URI` / `GOOGLE_ADS_OAUTH_REDIRECT_URI` and
`NEXT_PUBLIC_API_BASE_URL` accordingly.

## Environment variables

See [`.env.example`](../.env.example) for the complete list. Key groups:

| Group | Variables |
| --- | --- |
| Core | `ENVIRONMENT`, `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY` |
| Database | `POSTGRES_USER/PASSWORD/DB/HOST/PORT` |
| Redis | `REDIS_HOST/PORT/PASSWORD/DB` |
| Google | `GOOGLE_CLIENT_ID/SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `GOOGLE_ADS_OAUTH_REDIRECT_URI`, `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID` |
| AI | `AI_PROVIDER`, `AI_API_KEY`, `AI_BASE_URL`, `AI_DEFAULT_MODEL` |
| Email | `SMTP_HOST/PORT/USER/PASSWORD`, `EMAIL_FROM` |
| Safety | `SAFETY_MAX_DAILY_BUDGET` |
| Observability | `SENTRY_DSN` |
| Frontend | `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_NAME` |

**Secrets** are never committed. `ENCRYPTION_KEY` (Fernet) encrypts stored Google
OAuth tokens — generate with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
The architecture is secret-manager ready: any injector that populates the
environment (Docker secrets, AWS/GCP secret managers, Vault) works unchanged.

## Security posture

- JWT access + refresh with rotation & reuse detection; refresh token in an
  httpOnly cookie.
- Google OAuth tokens encrypted at rest (Fernet).
- Rate limiting on auth + AI/optimization endpoints (Redis-backed, enforced in
  staging/production).
- Security headers + per-request id on every response (`app/core/middleware.py`).
- Strict input validation (Pydantic/Zod), parameterized ORM (no raw SQL), CORS
  allow-list, audit + optimization logs.

## Monitoring

- `GET /health` — liveness · `GET /api/v1/health/ready` — readiness (DB + Redis).
- Structured JSON logs (structlog) with request id, method, path, status,
  duration. Set `SENTRY_DSN` to enable error tracking.
