# syntax=docker/dockerfile:1.7
# Trener BACKEND — FastAPI + uv, optimised for Railway.app

# ─── Stage 1: build the virtual environment with uv ──────────────────────────
FROM ghcr.io/astral-sh/uv:0.5.13-python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install only deps first — this layer is cached until pyproject.toml or
# uv.lock change. --no-dev keeps ruff / pytest / mongomock out of the image.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy the application source and install the project itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ─── Stage 2: minimal runtime image (no uv, no toolchain) ────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Non-root user.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

# Copy the venv + source from the builder, owned by the unprivileged user.
COPY --from=builder --chown=app:app /app /app

USER app
EXPOSE 8080

# In-image probe — Railway has its own healthcheck; this just makes
# `docker run` tidy and lets you debug locally.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,sys,urllib.request as u; \
sys.exit(0 if u.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",8080)}/health',timeout=3).status==200 else 1)"

# Shell form so ${PORT} expands at runtime — Railway injects PORT per deploy.
CMD ["sh", "-c", "fastapi run main.py --host 0.0.0.0 --port ${PORT:-8080}"]
