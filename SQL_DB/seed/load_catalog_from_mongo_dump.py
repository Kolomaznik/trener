"""Seed PostgreSQL ``catalog`` tabulky ze stromu JSON souborů vytvořeného
``MONGO_DB/dump.py``.

Načte připojení z ``../.env`` (stejně jako ``manage.py``), vybere dump z
``../MONGO_DB/dumps/`` (default = nejnovější) a upsertuje každý dokument do
tabulky ``catalog`` přes ``INSERT … ON CONFLICT (name) DO UPDATE``.

Skripty není migrace — schéma řeší ``manage.py`` / yoyo. Tenhle loader je
idempotentní a může se přespustit kdykoliv proti čerstvějšímu dumpu.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DUMPS_DIR = ROOT.parent / "MONGO_DB" / "dumps"

# Musí být v souladu s migration 20260516120000_schema_initial_catalog.py.
# Pořadí je závazné — používá se přímo v INSERT statementu.
MUSCLE_COLUMNS: tuple[str, ...] = (
    "chest",
    "deltoids",
    "biceps",
    "triceps",
    "forearms",
    "abs",
    "obliques",
    "hip_flexors",
    "trapezius",
    "rhomboids",
    "lats",
    "lower_back",
    "quadriceps",
    "hamstrings",
    "glutes",
    "abductors",
    "adductors",
    "calves",
    "tibialis",
    "neck",
    "knees",
    "hands",
    "ankles",
    "feet",
)
MUSCLE_SET = frozenset(MUSCLE_COLUMNS)

SCALAR_COLUMNS = ("name", "title", "english_name", "description")
JSONB_COLUMNS = ("cadence", "media")
ALL_COLUMNS = SCALAR_COLUMNS + JSONB_COLUMNS + MUSCLE_COLUMNS

# INSERT INTO catalog (name, title, …) VALUES (%s, %s, …)
#   ON CONFLICT (name) DO UPDATE SET title = EXCLUDED.title, …
_PLACEHOLDERS = ", ".join(["%s"] * len(ALL_COLUMNS))
_COLUMNS_SQL = ", ".join(ALL_COLUMNS)
_UPDATE_SET = ", ".join(f"{c} = EXCLUDED.{c}" for c in ALL_COLUMNS if c != "name")
INSERT_SQL = (
    f"INSERT INTO catalog ({_COLUMNS_SQL}) VALUES ({_PLACEHOLDERS}) "
    f"ON CONFLICT (name) DO UPDATE SET {_UPDATE_SET}"
)


def _load_database_url() -> str:
    load_dotenv(ENV_FILE)
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        sys.exit(f"Chybí proměnná {exc.args[0]} — zkopíruj .env.example do .env a vyplň hodnoty.")


def _find_dumps() -> list[Path]:
    if not DUMPS_DIR.is_dir():
        sys.exit(f"Adresář {DUMPS_DIR} neexistuje — nejdřív spusť MONGO_DB/dump.py.")
    dumps = sorted(p for p in DUMPS_DIR.iterdir() if p.is_dir())
    if not dumps:
        sys.exit(f"V {DUMPS_DIR} nejsou žádné dumpy.")
    return dumps


def _select_dump(name: str | None) -> Path:
    dumps = _find_dumps()
    if name is None:
        return dumps[-1]
    for d in dumps:
        if d.name == name:
            return d
    available = ", ".join(d.name for d in dumps)
    sys.exit(f"Dump {name!r} nenalezen. Dostupné: {available}")


def _row_from_doc(doc: dict) -> tuple:
    name = doc.get("name") or doc.get("_id")
    if not name:
        raise ValueError(f"Dokument bez 'name'/'_id': {doc!r}")

    muscle_engagement = doc.get("muscle_engagement_percent") or {}
    unknown = set(muscle_engagement) - MUSCLE_SET
    if unknown:
        raise ValueError(
            f"Dokument {name!r} obsahuje neznámé svaly {sorted(unknown)}. "
            f"Přidej je do MUSCLE_COLUMNS a vytvoř ALTER TABLE migraci."
        )

    scalar_values = (
        name,
        doc["title"],
        doc.get("english_name"),
        doc["description"],
    )
    jsonb_values = (Jsonb(doc["cadence"]), Jsonb(doc.get("media") or {}))
    muscle_values = tuple(int(muscle_engagement.get(m, 0)) for m in MUSCLE_COLUMNS)
    return scalar_values + jsonb_values + muscle_values


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="load_catalog_from_mongo_dump",
        description="Seed catalog table from a MongoDB dump (JSON tree).",
    )
    parser.add_argument(
        "--dump",
        default=None,
        help="název dumpu pod MONGO_DB/dumps/ (default: nejnovější)",
    )
    args = parser.parse_args()

    database_url = _load_database_url()
    dump_dir = _select_dump(args.dump)
    exercises_dir = dump_dir / "exercises"
    if not exercises_dir.is_dir():
        sys.exit(f"V dumpu {dump_dir.name} chybí adresář 'exercises'.")

    rows: list[tuple] = []
    for path in sorted(exercises_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        rows.append(_row_from_doc(doc))

    if not rows:
        sys.exit(f"V {exercises_dir} nejsou žádné JSON soubory.")

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
        conn.commit()

    print(f"{len(rows)} catalog rows loaded from {dump_dir.name}")


if __name__ == "__main__":
    main()
