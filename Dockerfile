# syntax=docker/dockerfile:1
#
# Multi-stage build for the SalesIQ API.
#
# Changes from the previous revision:
#   * runs as a non-root user (it ran as root)
#   * declares a HEALTHCHECK against /health
#   * uses a venv copied wholesale instead of cherry-picking site-packages,
#     which previously missed console scripts and .pth files
#   * execs uvicorn directly so SIGTERM reaches the server and in-flight
#     requests drain, instead of going through `python -m api.main`
#   * legacy `ENV KEY VALUE` syntax replaced with `ENV KEY=VALUE`

# ---------------------------------------------------------------- builder
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Self-contained venv: simpler and more reliable to copy than site-packages.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    PORT=8000 \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:////app/data/salesiq.db \
    CHECKPOINT_DB_PATH=/app/data/checkpoints.sqlite

# curl is needed by HEALTHCHECK; keep the layer minimal otherwise.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 salesiq \
    && useradd --system --uid 1001 --gid salesiq --create-home salesiq

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=salesiq:salesiq . .
RUN chmod +x /app/docker-entrypoint.sh

# Writable volume for the SQLite database and LangGraph checkpoints.
RUN mkdir -p /app/data && chown -R salesiq:salesiq /app/data

USER salesiq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/health || exit 1

# The entrypoint validates configuration in PID 1 and exits non-zero if it is
# bad, instead of letting uvicorn's supervisor respawn dying workers forever.
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# exec form: uvicorn replaces the shell and receives SIGTERM directly.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--timeout-graceful-shutdown", "20", "--no-server-header"]
