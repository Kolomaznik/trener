"""Seed PostgreSQL ``exercises`` tabulky ze stromu JSON souborů vytvorenych
``MONGO_DB/dump.py``.

Nacte pripojeni z ``../.env``, vybere dump z ``../MONGO_DB/dumps/``
(default = nejnovejsi) a upsertuje kazdy dokument do tabulky
``exercises`` pres ``INSERT ... ON CONFLICT (exercise_name, user_email)
DO UPDATE``.

Tabulka ``exercises`` je N:M mezi ``users`` a ``catalog``. Z mongo dokumentu
se aktualne kopiruji jen pole, ktera mapuji na sloupce v PG schematu:
``exercise_name``, ``user_email``, ``completed``, ``created_at``. Stavove
fields (``user_level``, ``consecutive_successes``, ``level_history``) jsou
zamerne ignorovany -- prijdou v dalsi migraci.

Skript neni migrace -- schema resi ``manage.py`` / yoyo. Tenhle loader
je idempotentni a muze se prespoustet kdykoliv proti cerstvejsimu dumpu.
Radky, jejichz ``exercise_name`` neni v ``catalog`` nebo ``user_email``
neni v ``users``, se preskoci s warning -- castecny dump nezastavi beh.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DUMPS_DIR = ROOT.parent / "MONGO_DB" / "dumps"

# Musi byt v souladu s migration 20260518100146_schema_initial_exercises.py.
# Poradi je zavazne -- pouziva se primo v INSERT statementu.
COLUMNS = ("exercise_name", "user_email", "completed", "created_at")

_PLACEHOLDERS = ", ".join(["%s"] * len(COLUMNS))
_COLUMNS_SQL = ", ".join(COLUMNS)
_UPDATE_SET = ", ".join(
    f"{c} = EXCLUDED.{c}" for c in COLUMNS if c not in ("exercise_name", "user_email")
)
INSERT_SQL = (
    f"INSERT INTO exercises ({_COLUMNS_SQL}) VALUES ({_PLACEHOLDERS}) "
    f"ON CONFLICT (exercise_name, user_email) DO UPDATE SET {_UPDATE_SET}"
)


def _load_database_url() -> str:
    load_dotenv(ENV_FILE)
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        sys.exit(f"Chybi promenna {exc.args[0]} -- zkopiruj .env.example do .env a vypln hodnoty.")


def _find_dumps() -> list[Path]:
    if not DUMPS_DIR.is_dir():
        sys.exit(f"Adresar {DUMPS_DIR} neexistuje -- nejdriv spust MONGO_DB/dump.py.")
    dumps = sorted(p for p in DUMPS_DIR.iterdir() if p.is_dir())
    if not dumps:
        sys.exit(f"V {DUMPS_DIR} nejsou zadne dumpy.")
    return dumps


def _select_dump(name: str | None) -> Path:
    dumps = _find_dumps()
    if name is None:
        return dumps[-1]
    for d in dumps:
        if d.name == name:
            return d
    available = ", ".join(d.name for d in dumps)
    sys.exit(f"Dump {name!r} nenalezen. Dostupne: {available}")


def _parse_mongo_date(value: object) -> datetime | None:
    """Unwrap BSON Extended JSON ``{"$date": "..."}`` to ``datetime``."""
    if value is None:
        return None
    if isinstance(value, dict) and "$date" in value:
        value = value["$date"]
    if isinstance(value, str):
        # Mongo emits e.g. "2026-05-08T18:02:01.468Z"; fromisoformat handles
        # the trailing Z only on 3.11+.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unexpected date value: {value!r}")


def _row_from_doc(doc: dict) -> tuple:
    exercise_name = doc.get("exercise_name")
    user_email = doc.get("user_email")
    if not exercise_name or not user_email:
        raise ValueError(f"Dokument bez exercise_name/user_email: {doc!r}")
    return (
        exercise_name,
        user_email,
        bool(doc.get("completed", False)),
        _parse_mongo_date(doc.get("created_at")),
    )


def _load_existing_keys(cur: psycopg.Cursor) -> tuple[set[str], set[str]]:
    cur.execute("SELECT name FROM catalog")
    catalog_names = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT email FROM users")
    user_emails = {r[0] for r in cur.fetchall()}
    return catalog_names, user_emails


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="load_exercises_from_mongo_dump",
        description="Seed exercises table from a MongoDB dump (JSON tree).",
    )
    parser.add_argument(
        "--dump",
        default=None,
        help="nazev dumpu pod MONGO_DB/dumps/ (default: nejnovejsi)",
    )
    args = parser.parse_args()

    database_url = _load_database_url()
    dump_dir = _select_dump(args.dump)
    user_exercises_dir = dump_dir / "user_exercises"
    if not user_exercises_dir.is_dir():
        sys.exit(f"V dumpu {dump_dir.name} chybi adresar 'user_exercises'.")

    raw_rows: list[tuple] = []
    for path in sorted(user_exercises_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        raw_rows.append(_row_from_doc(doc))

    if not raw_rows:
        sys.exit(f"V {user_exercises_dir} nejsou zadne JSON soubory.")

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            catalog_names, user_emails = _load_existing_keys(cur)
            rows: list[tuple] = []
            skipped = 0
            for row in raw_rows:
                exercise_name, user_email, *_ = row
                if exercise_name not in catalog_names:
                    print(
                        f"WARN: skipping {user_email}/{exercise_name} -- "
                        f"exercise not in catalog"
                    )
                    skipped += 1
                    continue
                if user_email not in user_emails:
                    print(f"WARN: skipping {user_email}/{exercise_name} -- " f"user not in users")
                    skipped += 1
                    continue
                rows.append(row)
            if rows:
                cur.executemany(INSERT_SQL, rows)
        conn.commit()

    print(f"{len(rows)} exercises rows loaded from {dump_dir.name} " f"({skipped} skipped)")


if __name__ == "__main__":
    main()
