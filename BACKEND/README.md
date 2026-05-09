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

## Workout Sessions API

Nová sada endpointů pro ukládání a analýzu tréninkových sérií.

### `POST /workout-sessions`

Uloží výsledek jedné série do MongoDB kolekce `workout_sessions`.
Vyžaduje Bearer token (Google OAuth).

Backend automaticky doplní:
- `user_email` z tokenu
- `user_weight_kg` / `user_height_cm` z profilu uživatele
- `muscle_engagement_percent` z dokumentu cviku

**Vstup (`WorkoutSessionCreate`):**

```json
{
  "exercise_id": "pushups_level_1",
  "exercise_name": "Kliky o zeď",
  "started_at": "2026-05-03T10:00:00Z",
  "total_duration_sec": 60.0,
  "total_reps": 15,
  "set_number": 1,
  "events": [
    { "value": 1, "token": "jedna", "timestamp_ms": 1000, "timestamp_iso": "..." },
    { "value": 2, "token": "dva",   "timestamp_ms": 2000, "timestamp_iso": "..." }
  ]
}
```

**Odpověď:** `201 Created` – obohacený dokument včetně `id` a `saved_at`.

---

### `GET /workout-sessions/level/{exercise_id}`

Vrátí úroveň uživatele pro daný cvik na základě posledních 5 uložených sérií.
Vyžaduje Bearer token (Google OAuth).

**Výpočet úrovně** (průměr `total_reps` posledních 5 sérií oproti `progression_goals` cviku):

| Průměr opakování          | Úroveň         | `rest_seconds` |
|---------------------------|----------------|----------------|
| žádná historie            | `beginner`     | 90 s           |
| < `beginner.reps`         | `beginner`     | 90 s           |
| ≥ `beginner.reps`         | `intermediate` | 60 s           |
| ≥ `mastery.reps`          | `mastery`      | 45 s           |

**Odpověď (`UserLevelInfo`):**

```json
{
  "level": "intermediate",
  "recent_sets": [{ "total_reps": 20, "started_at": "...", "set_number": 1 }],
  "target_reps": 25,
  "target_sets": 2,
  "last_best_reps": 20,
  "rest_seconds": 60
}
```

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
