# syntax=docker/dockerfile:1

FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /build/frontend
RUN corepack enable

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TEAMTOOLS_DATA_DIR=/app/data \
    TEAMTOOLS_DB_PATH=/app/data/teamtools.db \
    TEAMTOOLS_FRONTEND_DIST=/app/frontend/dist \
    TEAMTOOLS_LOG_DIR=/app/logs \
    TEAMTOOLS_LOG_LEVEL=INFO \
    TEAMTOOLS_SEED_DEV_USERS=false

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY backend/ ./backend/
RUN python -m pip install --no-cache-dir ./backend

COPY scripts/ ./scripts/
COPY data/config/ ./data/config/
COPY data/modules/ ./data/modules/
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist/

RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
