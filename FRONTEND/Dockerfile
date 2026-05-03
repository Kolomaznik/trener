# backend/Dockerfile
FROM python:3.12-slim

# Instalace uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Kopírování konfiguračních souborů
COPY pyproject.toml uv.lock ./

# Instalace závislostí (vytvoří se .venv)
RUN uv sync --frozen --no-cache

# Kopírování zbytku kódu
COPY . .

# Spuštění aplikace (Railway očekává port z ENV variable $PORT)
CMD ["uv", "run", "fastapi", "run", "main.py", "--port", "8080"]
