# Trener Backend

FastAPI aplikace spravovaná pomocí [uv](https://docs.astral.sh/uv/).

## Požadavky
- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Instalace
```bash
uv sync
```

## Spuštění (dev)
```bash
uv run main.py
```
nebo přímo přes uvicorn:
```bash
uv run uvicorn main:app --reload
```

API běží na <http://127.0.0.1:8000>, dokumentace na `/docs`.

## User settings endpoint

Backend vrací základní nastavení uživatele přes:

```bash
GET /user/settings
```

Aktuálně vrací e-mail:

```json
{"email":"user@example.com"}
```

E-mail se nastavuje přes `.env`:

```bash
USER_EMAIL=user@example.com
```

Frontend tento e-mail používá jako `login_hint` při přesměrování na Google OAuth.

## Lint
```bash
uv run --group dev ruff check .
uv run --group dev ruff format .
```

## Pre-commit

Konfigurace `.pre-commit-config.yaml` žije zde v `BACKEND/`, ale git repozitář je o úroveň
výš — hook proto instalujeme s explicitní cestou ke konfiguraci.

Jednorázová instalace git hooku (po `uv sync`), spouštěné ze složky `BACKEND/`:
```bash
uv run pre-commit install -c .pre-commit-config.yaml
```
Ručně přes všechny soubory:
```bash
uv run pre-commit run --all-files -c .pre-commit-config.yaml
```
