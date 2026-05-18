"""Backfill ``workout`` table z Mongo ``exercise_series`` dumpu.

Pro každý unikátní pár ``(user_email, datum z started_at)`` v dumpu vytvoří
jeden řádek v ``workout``. ``plan`` se počítá serverově z aktuálního stavu
SQL ``exercises`` (jmenovku každého cviku daného uživatele) — všechny
backfillnuté workouty proto dostanou stejný plán. Není to rekonstrukce
reálné historie, jen vyplnění datového modelu pro dev.

Idempotentní (``ON CONFLICT (user_email, day) DO NOTHING``) — opakované
spuštění proti čerstvějšímu dumpu jen přidá nové dvojice.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DUMPS_DIR = ROOT.parent / "MONGO_DB" / "dumps"

INSERT_SQL = """
    INSERT INTO workout (user_email, day, plan)
    SELECT %s, %s,
           COALESCE(
             (SELECT jsonb_agg(exercise_name ORDER BY exercise_name)
                FROM exercises
               WHERE user_email = %s),
             '[]'::jsonb
           )
    ON CONFLICT (user_email, day) DO NOTHING
"""


def _load_database_url() -> str:
    load_dotenv(ENV_FILE)
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        sys.exit(f"Chybí proměnná {exc.args[0]} — zkopíruj .env.example do .env a vyplň hodnoty.")


def _parse_mongo_date(value: object) -> datetime | None:
    """Rozbalí BSON Extended JSON wrapper ``{"$date": "..."}`` na ``datetime``."""
    if isinstance(value, dict) and set(value) == {"$date"}:
        return datetime.fromisoformat(value["$date"].replace("Z", "+00:00"))
    return None


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


def _collect_pairs(series_dir: Path) -> set[tuple[str, date]]:
    """Projde ``exercise_series/*.json`` a vrátí množinu ``(user_email, day)``."""
    pairs: set[tuple[str, date]] = set()
    skipped_no_email = 0
    skipped_no_date = 0
    for path in sorted(series_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        email = doc.get("user_email")
        if not isinstance(email, str):
            skipped_no_email += 1
            continue
        started = _parse_mongo_date(doc.get("started_at"))
        if started is None:
            skipped_no_date += 1
            continue
        pairs.add((email, started.date()))
    if skipped_no_email:
        print(f"  warning: {skipped_no_email} series bez user_email — přeskočeno")
    if skipped_no_date:
        print(f"  warning: {skipped_no_date} series bez started_at — přeskočeno")
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="load_workouts_from_mongo_dump",
        description="Backfill workout rows from MongoDB exercise_series dump.",
    )
    parser.add_argument(
        "--dump",
        default=None,
        help="název dumpu pod MONGO_DB/dumps/ (default: nejnovější)",
    )
    args = parser.parse_args()

    database_url = _load_database_url()
    dump_dir = _select_dump(args.dump)
    series_dir = dump_dir / "exercise_series"
    if not series_dir.is_dir():
        sys.exit(f"V dumpu {dump_dir.name} chybí adresář 'exercise_series'.")

    pairs = _collect_pairs(series_dir)
    if not pairs:
        sys.exit(f"V {series_dir} nejsou žádné použitelné série.")

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users")
            known_emails = {row[0] for row in cur.fetchall()}

            valid = sorted((email, day) for email, day in pairs if email in known_emails)
            orphan_emails = sorted({email for email, _ in pairs} - known_emails)

            if orphan_emails:
                preview = ", ".join(orphan_emails[:5])
                more = f" (+{len(orphan_emails) - 5} dalších)" if len(orphan_emails) > 5 else ""
                skipped_count = len(pairs) - len(valid)
                print(
                    f"  warning: {skipped_count} párů přeskočeno kvůli "
                    f"neznámým user_email: {preview}{more}"
                )

            if valid:
                rows = [(email, day, email) for email, day in valid]
                cur.executemany(INSERT_SQL, rows)
        conn.commit()

    written = len(valid)
    skipped = len(pairs) - written
    print(
        f"{written} workout rows written, {skipped} skipped (orphan user_email), "
        f"{len(pairs)} total unique (user, day) pairs in {dump_dir.name}"
    )


if __name__ == "__main__":
    main()
