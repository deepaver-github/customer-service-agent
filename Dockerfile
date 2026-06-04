# syntax=docker/dockerfile:1.7

# ---- Frontend build stage ----
FROM node:20-slim AS frontend
WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# angular.json's outputPath is "../app/static" relative to /build/frontend,
# so the bundle lands at /build/app/static.
RUN npm run build


# ---- Backend runtime stage ----
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install runtime dependencies as their own cacheable layer.
# Mirrors pyproject.toml [project].dependencies — keep in sync.
RUN pip install \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.32.0" \
        "anthropic>=0.42.0" \
        "sqlalchemy[asyncio]>=2.0.0" \
        "aiosqlite>=0.20.0" \
        "asyncpg>=0.30.0" \
        "pydantic-settings>=2.6.0" \
        "pyyaml>=6.0.0" \
        "structlog>=24.0.0" \
        "httpx>=0.27.0" \
        "sse-starlette>=2.0.0" \
        "alembic>=1.14.0"

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini agent_config.yaml ./

COPY --from=frontend /build/app/static/ ./app/static/

EXPOSE 8001
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
