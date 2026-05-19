# SQL_DB

Migrační projekt pro PostgreSQL databázi projektu **trener**. Postaven nad knihovnou [`yoyo-migrations`](https://ollycope.com/software/yoyo/latest/) s vlastním tenkým CLI wrapperem (`manage.py`), který načítá konfiguraci z `.env`.

Sourozenec [`MONGO_DB/`](../MONGO_DB/) — postupně přebírá kolekce z MongoDB. Aktuálně migrované: **catalog** (immutable seznam cviků), **users** (účty + profil) a **exercises** (N:M mezi users a catalog — které cviky si uživatel přidal).

Spravuje:

- **Schéma tabulek + indexy** (kategorie `schema`)
- **Datové transformace** existujících řádků (kategorie `transform`)
- _Seed data_ pro každou migrovanou kolekci ze standalone skriptů v [`seed/`](seed/) — viz níže.

## Schema

Aktuální stav PostgreSQL tabulek. Pro Mongo kolekce, které ještě nejsou migrované, viz [MONGO_DB/](../MONGO_DB/).

```mermaid
erDiagram
    CATALOG {
        text name PK
        text title
        text english_name
        text description
        jsonb goal
        jsonb muscle_engagement
    }
    CATALOG_MEDIA {
        text exercise_name PK,FK
        text name PK
        text data
    }
    USERS {
        text email PK
        text sub UK
        text name
        text picture
        int birth_year
        int height_cm "CHECK 50-250"
        double weight_kg "CHECK 20-300"
        text gender "CHECK male/female"
        timestamptz created_at
    }
    EXERCISES {
        text exercise_name PK,FK
        text user_email PK,FK
        date completed_at
        date created_at
    }
    WORKOUT {
        text user_email PK,FK
        date day PK
        jsonb plan
    }
    WORKOUT_SERIES {
        text user_email PK,FK
        date day PK,FK
        text exercise_name PK,FK
        time time PK
        int set_number
        int total_reps
        int target_reps
        double total_duration_sec
        jsonb counting
        jsonb evaluation
        text user_level
    }
    CATALOG ||--o{ CATALOG_MEDIA : "has"
    USERS ||--o{ EXERCISES : "has"
    USERS ||--o{ WORKOUT : "has"
    CATALOG ||--o{ EXERCISES : "referenced by"
    EXERCISES }o--o{ WORKOUT : "in plan"
    WORKOUT ||--o{ WORKOUT_SERIES : "logs"
    CATALOG ||--o{ WORKOUT_SERIES : "set of"
```

### `catalog_media`

Jeden řádek = jeden obrázek nebo video k cviku. Composite PK je `(exercise_name, name)`; `exercise_name` je FK do `catalog(name)` s `ON DELETE CASCADE`. `data` drží celý `data:image/...;base64,...` URI tak, jak přišel z dumpu.

| Sloupec | Typ | Null | Popis |
| --- | --- | --- | --- |
| `exercise_name` | `TEXT` PK, FK → `catalog(name)` ON DELETE CASCADE | NOT NULL | Cvik, ke kterému media patří. |
| `name` | `TEXT` PK | NOT NULL | Slot v rámci cviku — např. `front`, `back`, `demo`. |
| `data` | `TEXT` | NOT NULL | `data:image/...;base64,...` URI nebo HTTPS URL. Backend ji posílá frontendu beze změny. |

### `workout_series`

Jeden řádek = jeden zalogovaný set. Composite PK je `(user_email, day, exercise_name, time)`. Dvě FK:
- `exercise_name` → `catalog(name)` ON DELETE CASCADE
- `(user_email, day)` → `workout(user_email, day)` ON DELETE CASCADE (vyžaduje existující parent workout)

| Sloupec | Typ | Null | Popis |
| --- | --- | --- | --- |
| `user_email` | `TEXT` PK, FK | NOT NULL | Vlastník workoutu. |
| `day` | `DATE` PK, FK | NOT NULL | Datum workoutu (z parent `workout.day`). |
| `exercise_name` | `TEXT` PK, FK → `catalog(name)` | NOT NULL | Cvik, ke kterému set patří. |
| `time` | `TIME` PK | NOT NULL | Wall-clock čas startu setu (microsecond precision); diskriminátor mezi sety stejného cviku v rámci dne. |
| `set_number` | `INT` | NOT NULL | Pořadí setu v rámci cviku v ten den (1-indexed). |
| `total_reps` | `INT` | NOT NULL | Skutečný počet opakování v setu. |
| `target_reps` | `INT` | NULL | Cíl pro set (z `catalog.goal.reps` v okamžiku startu); chybí na starších záznamech. |
| `total_duration_sec` | `DOUBLE PRECISION` | NOT NULL | Délka setu v sekundách. |
| `counting` | `JSONB` | NOT NULL `DEFAULT '[]'::jsonb` | Pole per-rep eventů (viz [JSONB columns](#jsonb-columns)). |
| `evaluation` | `JSONB` | NULL | Vyhodnocení setu (pace, trend, recommendation) — viz [JSONB columns](#jsonb-columns). |
| `user_level` | `TEXT` | NULL | Tier uživatele v okamžiku setu (`beginner`/`intermediate`/`mastery`). |

## JSONB columns

Konkrétní příklady payloadů pro každý JSONB sloupec — užitečné pro debugování a psaní `->>` / `->` dotazů.

### `catalog.goal`

Cíl pro jeden cvik: počet sérií a opakování. Hodnoty pocházejí ze dvou různých tierů původního Mongo `progression_goals` (reps z intermediate, sets z mastery) — viz [seed/load_catalog_from_mongo_dump.py](seed/load_catalog_from_mongo_dump.py) (`_extract_goal`).

```json
{
  "sets": 3,
  "reps": 25
}
```

Příklad dotazu:

```sql
SELECT name, (goal->>'sets')::int AS sets, (goal->>'reps')::int AS reps
  FROM catalog
 WHERE (goal->>'reps')::int >= 20
 ORDER BY (goal->>'reps')::int DESC;
```

### `catalog.muscle_engagement`

Variabilní mapa `<muscle_name> → percent` (int 0–100). Klíče jsou volné — nový sval prostě jen přibyde v JSONB, schema se nemění. Suma hodnot u jednoho cviku nemusí dělat 100 % (vyjadřuje relativní zapojení).

```json
{
  "chest": 40,
  "triceps": 30,
  "deltoids": 15,
  "abs": 5,
  "lower_back": 5,
  "hands": 5
}
```

Příklady dotazu:

```sql
-- Cviky, které zapojují prsa
SELECT name FROM catalog WHERE muscle_engagement ? 'chest';

-- Cviky se zapojením prsou >= 30 %
SELECT name, (muscle_engagement->>'chest')::int AS chest_pct
  FROM catalog
 WHERE (muscle_engagement->>'chest')::int >= 30
 ORDER BY chest_pct DESC;

-- Cviky pokrývající všechny zadané svaly najednou
SELECT name FROM catalog
 WHERE muscle_engagement ?& array['chest','triceps','deltoids'];
```

### `workout.plan`

JSONB pole jmen cviků (`exercise_name`), jak byly aktivní (`exercises.completed_at IS NULL`) v okamžiku, kdy uživatel poprvé požádal o dnešní trénink. Snapshot — další přidání/dokončení cviků během dne se v `plan` neprojeví.

```json
["pushups_level_1", "bridges_level_1", "squats_level_1"]
```

`PUT /workout` upsertuje řádek `(user_email, CURRENT_DATE)`. První volání naplní `plan` z `exercises`; další volání v ten samý den jen vrátí už uložený plan (ON CONFLICT DO NOTHING).

### `workout_series.counting`

Pole per-rep eventů z voice-counting flow. Každý prvek nese vlastní timestamp + zda byl skutečně rozpoznán nebo interpolován mezi dvěma rozpoznanými.

```json
[
  {"value": 1, "token": "1", "timestamp_ms": 1778309068671, "timestamp_iso": "2026-05-09T06:44:28.671000+00:00", "interpolated": true},
  {"value": 2, "token": "2", "timestamp_ms": 1778309071686, "timestamp_iso": "2026-05-09T06:44:31.686Z", "interpolated": false},
  {"value": 3, "token": "3", "timestamp_ms": 1778309072123, "timestamp_iso": "2026-05-09T06:44:32.123Z", "interpolated": false}
]
```

Příklad dotazu:

```sql
-- Sety, kde víc než polovina opakování byla interpolovaná
SELECT user_email, day, exercise_name, time
  FROM workout_series
 WHERE jsonb_array_length(counting) > 0
   AND (
     SELECT count(*) FILTER (WHERE (e->>'interpolated')::bool)
       FROM jsonb_array_elements(counting) AS e
   ) * 2 > jsonb_array_length(counting);
```

### `workout_series.evaluation`

Fixní struktura — vyhodnocení setu vůči tempu, trendu a target_reps. `NULL` pro starší záznamy, které ho nemají.

```json
{
  "pace_label": "too_fast",
  "trend_label": "steady",
  "repetition_label": "too_few",
  "avg_interval_sec": 0.44,
  "recommendation": "Tempo je příliš rychlé. Zpomal na 6s/rep a soustřeď se na formu.",
  "is_completed": false
}
```

Příklad dotazu:

```sql
-- Splněné sety za poslední týden
SELECT user_email, day, exercise_name, total_reps
  FROM workout_series
 WHERE day >= CURRENT_DATE - INTERVAL '7 days'
   AND (evaluation->>'is_completed')::bool;
```

Tabulka `users` nemá žádné JSONB sloupce — celý řádek jsou scalary.

Tabulka `exercises` je N:M mezi `users` a `catalog` s kompozitním PK `(exercise_name, user_email)`. Aktuálně drží jen `created_at` (datum, kdy si uživatel cvik přidal) a `completed_at` (datum, kdy ho označil za splněný; `NULL` = ještě nesplněn). Per-user state machine z Monga (`user_level`, `consecutive_successes`, `level_history`) přijde v další migraci — pole se loaderem zatím ignorují.

## Instalace

```bash
cd SQL_DB
uv sync
```

## Konfigurace

```bash
cp .env.example .env
# vyplň DATABASE_URL
```

| Proměnná       | Popis                              | Příklad                                                  |
| -------------- | ---------------------------------- | -------------------------------------------------------- |
| `DATABASE_URL` | PostgreSQL connection string       | `postgresql://user:pass@host:5432/trener`                |

Podporované hostingy: Supabase, Neon, lokální Postgres (přes Docker).

## Lokální Postgres (volitelné)

```bash
docker run -d --name trener-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:17
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

## Použití

```bash
# aplikuj všechny pending migrace
uv run python manage.py up

# aplikuj migrace pouze do daného migration id (včetně)
uv run python manage.py up --to 20260517120000

# rollback aplikovaných migrací do daného id (exclusive — vše novější se odrolovat)
uv run python manage.py down --to 20260516120000

# výpis migrací (applied/pending)
uv run python manage.py status

# DESTRUKTIVNÍ: zahodí celé public schéma (data, tabulky, yoyo metastore)
# a vytvoří ho znovu prázdné. Pak je potřeba znovu spustit `up`.
# Default je interaktivní potvrzení; pro CI/skripty přidej `--yes`.
uv run python manage.py clear
uv run python manage.py clear --yes

# vytvoř novou migraci se správným timestamp prefixem
uv run python manage.py new schema add_user_exercises_table
uv run python manage.py new transform catalog_split_family
```

## Seed: import z MongoDB dumpu

Loadery čtou nejnovější dump pod [`../MONGO_DB/dumps/`](../MONGO_DB/dumps/). Všechny jsou idempotentní (`INSERT … ON CONFLICT DO UPDATE`) — opakované spuštění proti čerstvějšímu dumpu jen aktualizuje data.

### `catalog`

```bash
# default: nejnovější dump
uv run python seed/load_catalog_from_mongo_dump.py

# konkrétní dump
uv run python seed/load_catalog_from_mongo_dump.py --dump 2026-05-15_084622
```

### `users`

```bash
uv run python seed/load_users_from_mongo_dump.py
uv run python seed/load_users_from_mongo_dump.py --dump 2026-05-15_084622
```

### `exercises`

```bash
uv run python seed/load_exercises_from_mongo_dump.py
uv run python seed/load_exercises_from_mongo_dump.py --dump 2026-05-15_084622
```

Vyžaduje, aby už byly nasypané `catalog` a `users` — řádky, které odkazují na chybějící `exercise_name` nebo `user_email`, loader přeskočí s warning (FK by stejně spadlo).

Loader rozbalí BSON Extended JSON wrappery (`$oid`, `$date`) bez závislosti na `pymongo`.

### `workouts`

Backfill historických tréninků z Mongo `exercise_series` kolekce. Pro každý unikátní pár `(user_email, datum z started_at)` vytvoří jeden řádek v `workout`. **Všechny řádky dostanou stejný `plan`** — aktuální seznam cviků daného uživatele ze SQL `exercises`. Není to rekonstrukce reálné historie, jen vyplnění datového modelu pro dev.

```bash
uv run python seed/load_workouts_from_mongo_dump.py
uv run python seed/load_workouts_from_mongo_dump.py --dump 2026-05-18_213640
```

Vyžaduje, aby už byly nasypané `users` a `exercises` (jinak `plan` skončí jako prázdné pole nebo páry s neznámým `user_email` se přeskočí). Idempotentní přes `ON CONFLICT (user_email, day) DO NOTHING` — re-run jen přidá nové dvojice.

### `workout_series`

Backfill set-level záznamů z Mongo `exercise_series`. Pro každý dokument vytvoří jeden řádek `(user_email, day, exercise_name, time)` se všemi metrickými poli (`counting`, `evaluation`, `total_reps`, ...).

```bash
uv run python seed/load_series_from_mongo_dump.py
uv run python seed/load_series_from_mongo_dump.py --dump 2026-05-18_213640
```

Vyžaduje už nasypané `workouts` (composite FK target — bez parent řádku v `workout` INSERT spadne). Páry s neznámou `(user_email, day)` se přeskočí s warningem. Idempotentní přes `ON CONFLICT (user_email, day, exercise_name, time) DO NOTHING`.

## Naming konvence migrací

```
<YYYYMMDDhhmmss>_<kategorie>_<popis_snake_case>.py
```

- **kategorie** ∈ `schema`, `seed`, `transform`
- timestamp generuje `manage.py new` automaticky
- **obsah souboru pouze ASCII** — yoyo čte migrace přes `open(path)` bez `encoding=`, což na Windows defaultuje na cp1252 a spadne na vícebyte UTF-8 sekvenci. Český text patří do README/loaderů, ne do migrací.

Příklad: `20260517120000_schema_initial_users.py`

## Šablona migrace

```python
from yoyo import step

__depends__: set[str] = set()

steps = [
    step(
        """
        CREATE TABLE example (id BIGSERIAL PRIMARY KEY);
        """,
        "DROP TABLE IF EXISTS example;",
    ),
]
```

`yoyo` drží stav aplikovaných migrací v tabulkách `_yoyo_migration`, `_yoyo_log` a používá advisory lock `_yoyo_lock` (vytvoří se automaticky při prvním běhu).

## Verifikace

```bash
# 1. instalace dependencí
uv sync

# 2. lokální Postgres přes Docker (volitelné)
docker run -d --name trener-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:17

# 3. konfigurace
cp .env.example .env
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# 4. první spuštění migrací
uv run python manage.py up

# 5. seed všech kolekcí z aktuálního Mongo dumpu
uv run python seed/load_catalog_from_mongo_dump.py
uv run python seed/load_users_from_mongo_dump.py
uv run python seed/load_exercises_from_mongo_dump.py

# 6. ověření obsahu
psql "$DATABASE_URL" -c "SELECT name, muscle_engagement FROM catalog ORDER BY name;"
psql "$DATABASE_URL" -c "SELECT email, sub, height_cm, weight_kg, created_at FROM users;"
psql "$DATABASE_URL" -c "SELECT user_email, exercise_name, completed_at, created_at FROM exercises ORDER BY exercise_name;"

# 7. druhé spuštění seedu musí být no-op pro počet řádků (ON CONFLICT)
uv run python seed/load_catalog_from_mongo_dump.py
uv run python seed/load_users_from_mongo_dump.py
uv run python seed/load_exercises_from_mongo_dump.py
```

## Pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
