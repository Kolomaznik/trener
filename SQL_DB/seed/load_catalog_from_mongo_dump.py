"""Seed PostgreSQL ``catalog`` (a souvisejících ``media``) tabulek ze stromu
JSON souborů vytvořeného ``MONGO_DB/dump.py``.

Načte připojení z ``../.env`` (stejně jako ``manage.py``), vybere dump z
``../MONGO_DB/dumps/`` (default = nejnovější) a upsertuje každý dokument do
tabulky ``catalog`` přes ``INSERT … ON CONFLICT (name) DO UPDATE``. Současně
rozloží Mongo pole ``media`` (dict ``{slot: data_uri}``) do samostatných
řádků v tabulce ``media`` (composite PK ``(exercise_name, name)``).

Skripty není migrace — schéma řeší ``manage.py`` / yoyo. Tenhle loader je
idempotentní a může se přespustit kdykoliv proti čerstvějšímu dumpu; obě
upserty běží ve stejné transakci.
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
SCALAR_COLUMNS = ("name", "title", "english_name", "description")
JSONB_COLUMNS = ("goal", "muscle_engagement")
ALL_COLUMNS = SCALAR_COLUMNS + JSONB_COLUMNS

# INSERT INTO catalog (name, title, …) VALUES (%s, %s, …)
#   ON CONFLICT (name) DO UPDATE SET title = EXCLUDED.title, …
_PLACEHOLDERS = ", ".join(["%s"] * len(ALL_COLUMNS))
_COLUMNS_SQL = ", ".join(ALL_COLUMNS)
_UPDATE_SET = ", ".join(f"{c} = EXCLUDED.{c}" for c in ALL_COLUMNS if c != "name")
CATALOG_INSERT_SQL = (
    f"INSERT INTO catalog ({_COLUMNS_SQL}) VALUES ({_PLACEHOLDERS}) "
    f"ON CONFLICT (name) DO UPDATE SET {_UPDATE_SET}"
)

MEDIA_INSERT_SQL = (
    "INSERT INTO catalog_media (exercise_name, name, data) VALUES (%s, %s, %s) "
    "ON CONFLICT (exercise_name, name) DO UPDATE SET data = EXCLUDED.data"
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


def _extract_goal(doc: dict) -> dict:
    """Sbalí Mongo ``progression_goals`` třístupňový strom do jednoho cíle.

    Per user spec: ``reps`` z intermediate tieru, ``sets`` z mastery tieru.
    Vrátí ``{"sets": int|None, "reps": int|None}`` — chybějící hodnoty
    skončí jako JSON ``null``.
    """
    goals = doc.get("progression_goals") or {}
    return {
        "sets": (goals.get("mastery") or {}).get("sets"),
        "reps": (goals.get("intermediate") or {}).get("reps"),
    }


def _exercise_name(doc: dict) -> str:
    name = doc.get("name") or doc.get("_id")
    if not name:
        raise ValueError(f"Dokument bez 'name'/'_id': {doc!r}")
    return name


def _catalog_row(doc: dict) -> tuple:
    # Mongo field is ``muscle_engagement_percent`` — v PG je sloupec
    # přejmenovaný na ``muscle_engagement`` (procenta jsou implicitní).
    return (
        _exercise_name(doc),
        doc["title"],
        doc.get("english_name"),
        doc["description"],
        Jsonb(_extract_goal(doc)),
        Jsonb(doc.get("muscle_engagement_percent") or {}),
    )


def _media_rows(doc: dict) -> list[tuple]:
    """Rozloží ``doc["media"]`` (dict ``{slot: data_uri}``) na řádky pro
    tabulku ``media``. Prázdné nebo chybějící ``media`` -> prázdný seznam."""
    name = _exercise_name(doc)
    media = doc.get("media") or {}
    return [(name, slot, data) for slot, data in media.items()]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="load_catalog_from_mongo_dump",
        description="Seed catalog + media tables from a MongoDB dump (JSON tree).",
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

    catalog_rows: list[tuple] = []
    media_rows: list[tuple] = []
    for path in sorted(exercises_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        catalog_rows.append(_catalog_row(doc))
        media_rows.extend(_media_rows(doc))

    if not catalog_rows:
        sys.exit(f"V {exercises_dir} nejsou žádné JSON soubory.")

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.executemany(CATALOG_INSERT_SQL, catalog_rows)
            if media_rows:
                cur.executemany(MEDIA_INSERT_SQL, media_rows)
        conn.commit()

    print(
        f"{len(catalog_rows)} catalog rows, {len(media_rows)} media rows "
        f"loaded from {dump_dir.name}"
    )


if __name__ == "__main__":
    main()
