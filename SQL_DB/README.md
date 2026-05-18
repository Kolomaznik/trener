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
        bool completed
        timestamptz created_at
    }
    CATALOG ||--o{ CATALOG_MEDIA : "has"
    USERS ||--o{ EXERCISES : "has"
    CATALOG ||--o{ EXERCISES : "referenced by"
```

### `catalog_media`

Jeden řádek = jeden obrázek nebo video k cviku. Composite PK je `(exercise_name, name)`; `exercise_name` je FK do `catalog(name)` s `ON DELETE CASCADE`. `data` drží celý `data:image/...;base64,...` URI tak, jak přišel z dumpu.

| Sloupec | Typ | Null | Popis |
| --- | --- | --- | --- |
| `exercise_name` | `TEXT` PK, FK → `catalog(name)` ON DELETE CASCADE | NOT NULL | Cvik, ke kterému media patří. |
| `name` | `TEXT` PK | NOT NULL | Slot v rámci cviku — např. `front`, `back`, `demo`. |
| `data` | `TEXT` | NOT NULL | `data:image/...;base64,...` URI nebo HTTPS URL. Backend ji posílá frontendu beze změny. |

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

Tabulka `users` nemá žádné JSONB sloupce — celý řádek jsou scalary.

Tabulka `exercises` je N:M mezi `users` a `catalog` s kompozitním PK `(exercise_name, user_email)`. Aktuálně drží jen `completed` a `created_at` (kdy si uživatel cvik přidal). Per-user state machine z Monga (`user_level`, `consecutive_successes`, `level_history`) přijde v další migraci — pole se loaderem zatím ignorují.

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
psql "$DATABASE_URL" -c "SELECT user_email, exercise_name, completed, created_at FROM exercises ORDER BY exercise_name;"

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
