# MONGO_DB

Migrační projekt pro plnění a údržbu dat v MongoDB databázi projektu **trener**. Postaven nad knihovnou [`mongodb-migrations`](https://pypi.org/project/mongodb-migrations/) s vlastním tenkým CLI wrapperem (`manage.py`), který načítá konfiguraci z `.env`.

Spravuje:

- **Schéma kolekcí + indexy** (kategorie `schema`)
- **Seed data / fixtures** (kategorie `seed`)
- **Datové transformace** existujících dokumentů (kategorie `transform`)

## Instalace

```bash
cd MONGO_DB
uv sync
```

`uv sync` vytvoří `.venv` a doinstaluje závislosti dle `pyproject.toml`.

## Konfigurace

```bash
cp .env.example .env
# vyplň MONGO_URI a MONGO_DB_NAME
```

`.env` obsahuje:

| Proměnná         | Popis                                    | Příklad                            |
| ---------------- | ---------------------------------------- | ---------------------------------- |
| `MONGO_URI`      | připojovací řetězec (může i s databází)  | `mongodb://localhost:27017`        |
| `MONGO_DB_NAME`  | název databáze (pokud chybí v URI)       | `trener`                           |

## Lokální MongoDB (volitelné)

Nejrychleji přes Docker:

```bash
docker run -d --name trener-mongo -p 27017:27017 mongo:7
```

## Použití

Wrapper `manage.py` se spouští přes `uv run`:

```bash
# aplikuj všechny pending migrace
uv run python manage.py up

# aplikuj migrace pouze do daného timestampu (včetně)
uv run python manage.py up --to 20260425000002

# rollback aplikovaných migrací do daného timestampu (exclusive)
uv run python manage.py down --to 20260425000002

# výpis aplikovaných migrací z metastore kolekce
uv run python manage.py status

# vytvoř novou migraci se správným timestamp prefixem
uv run python manage.py new schema add_workouts_collection
uv run python manage.py new seed default_workout_templates
uv run python manage.py new transform exercises_split_name
```

## Dump a restore databáze

Mimo migrace jsou k dispozici dva standalone skripty pro zálohu a obnovu dat.
Oba načítají připojení z `.env` stejně jako `manage.py`.

### `dump.py`

Uloží každý dokument jako samostatný JSON soubor (BSON Extended JSON, takže
`ObjectId`/`datetime` zůstanou zachované):

```bash
uv run python dump.py
```

Struktura výstupu:

```
dumps/<YYYY-MM-DD_HHMMSS>/<collection_name>/<record_id>.json
```

Adresář `dumps/` je v `.gitignore` — zálohy se necommitují.

### `restore.py`

Nahraje dokumenty z dumpu zpět do databáze.

```bash
# vypíše nalezené dumpy a nechá vybrat (Enter = nejnovější)
uv run python restore.py

# bez ptaní vezme nejnovější dump
uv run python restore.py --latest

# před nahráním zahodí všechny kolekce v cílové databázi
uv run python restore.py --latest --clean
```

Bez `--clean` se dokumenty upsertují podle `_id` (existující se přepíšou).

## Naming konvence migrací

```
<YYYYMMDDhhmmss>_<kategorie>_<popis_snake_case>.py
```

- **kategorie** ∈ `schema`, `seed`, `transform`
- **popis** pouze `[_a-z]` — žádné číslice, žádné velké písmeno (omezení regexu knihovny `mongodb-migrations`)
- timestamp generuje `manage.py new` automaticky

Příklad: `20260425143022_schema_add_workouts_collection.py`

## Šablona migrace

```python
from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        # přístup k databázi přes self.db (pymongo Database)
        ...

    def downgrade(self):
        ...
```

`mongodb-migrations` udržuje stav aplikovaných migrací v kolekci `database_migrations` (default metastore).

## Verifikace

```bash
# 1. instalace dependencí
uv sync

# 2. lokální Mongo přes Docker (volitelné)
docker run -d --name trener-mongo -p 27017:27017 mongo:7

# 3. konfigurace
cp .env.example .env

# 4. první spuštění migrací
uv run python manage.py up

# 5. druhé spuštění musí být no-op (ověření idempotence + trackingu)
uv run python manage.py up

# 6. ověření metastore kolekce
uv run python manage.py status
```

## Pre-commit

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Hooks: `ruff` (check + format), trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-added-large-files (sjednoceno s `BACKEND/.pre-commit-config.yaml`).
