# SQL_DB

Migrační projekt pro PostgreSQL databázi projektu **trener**. Postaven nad knihovnou [`yoyo-migrations`](https://ollycope.com/software/yoyo/latest/) s vlastním tenkým CLI wrapperem (`manage.py`), který načítá konfiguraci z `.env`.

Sourozenec [`MONGO_DB/`](../MONGO_DB/) — postupně přebírá kolekce z MongoDB. První na řadě je **catalog** (immutable seznam cviků).

Spravuje:

- **Schéma tabulek + indexy** (kategorie `schema`)
- **Datové transformace** existujících řádků (kategorie `transform`)
- _Seed data_ pro `catalog` se neřeší migrací, ale standalone skriptem [`seed/load_catalog_from_mongo_dump.py`](seed/load_catalog_from_mongo_dump.py) — viz níže.

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
uv run python manage.py up --to 20260516120000

# rollback aplikovaných migrací do daného id (exclusive — vše novější se odrolovat)
uv run python manage.py down --to 20260516120000

# výpis migrací (applied/pending)
uv run python manage.py status

# vytvoř novou migraci se správným timestamp prefixem
uv run python manage.py new schema add_users_table
uv run python manage.py new transform catalog_split_family
```

## Seed: catalog z MongoDB dumpu

Naplnění tabulky `catalog` z existujícího MongoDB dumpu pod [`../MONGO_DB/dumps/`](../MONGO_DB/dumps/):

```bash
# default: nejnovější dump
uv run python seed/load_catalog_from_mongo_dump.py

# konkrétní dump
uv run python seed/load_catalog_from_mongo_dump.py --dump 2026-05-15_084622
```

Loader je idempotentní (`INSERT … ON CONFLICT (name) DO UPDATE`) — opakované spuštění proti čerstvějšímu dumpu jen aktualizuje data.

## Naming konvence migrací

```
<YYYYMMDDhhmmss>_<kategorie>_<popis_snake_case>.py
```

- **kategorie** ∈ `schema`, `seed`, `transform`
- timestamp generuje `manage.py new` automaticky

Příklad: `20260516120000_schema_initial_catalog.py`

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

# 5. seed catalog z aktuálního Mongo dumpu
uv run python seed/load_catalog_from_mongo_dump.py

# 6. ověření obsahu
psql "$DATABASE_URL" -c "SELECT name, glutes, hamstrings FROM catalog ORDER BY name;"

# 7. druhé spuštění seedu musí být no-op pro počet řádků (ON CONFLICT)
uv run python seed/load_catalog_from_mongo_dump.py
```

## Pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
