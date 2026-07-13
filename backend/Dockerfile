# ===========================================================================
# Backend image — multi-stage, uv-based, Python 3.12 slim.
# Stages:  builder (deps) -> runtime (lean, non-root)
# ===========================================================================
FROM python:3.12-slim AS builder

# uv: fast, reproducible dependency installs
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (cached layer) using only project metadata
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -r <(uv pip compile pyproject.toml 2>/dev/null || echo "") \
    || uv pip install --system --no-cache \
        fastapi "uvicorn[standard]" gunicorn python-multipart \
        pydantic pydantic-settings email-validator \
        "sqlalchemy[asyncio]" alembic asyncpg psycopg2-binary \
        redis celery pyjwt "passlib[bcrypt]" cryptography authlib \
        httpx tenacity structlog jinja2 aiosmtplib slowapi

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

# Non-root user
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

# Copy installed site-packages + entrypoints from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Application source
COPY --chown=app:app . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
