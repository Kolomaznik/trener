"""Backfill ``workout_series`` table z Mongo ``exercise_series`` dumpu.

Pro každý dokument vytvoří jeden řádek ``(user_email, day, exercise_name,
time)`` s metrickými poli (counting, evaluation, total_reps, ...). Vyžaduje
už nasypané ``workouts`` (composite FK target); páry s neznámou
``(user_email, day)`` se přeskočí s warningem.

Idempotentní (``ON CONFLICT (user_email, day, exercise_name, time) DO
NOTHING``) — opakované spuštění proti čerstvějšímu dumpu jen přidá nové
řádky.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DUMPS_DIR = ROOT.parent / "MONGO_DB" / "dumps"

INSERT_SQL = """
    INSERT INTO workout_series (
        user_email, day, exercise_name, time,
        set_number, total_reps, target_reps, total_duration_sec,
        counting, evaluation, user_level
    ) VALUES (
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s
    )
    ON CONFLICT (user_email, day, exercise_name, time) DO NOTHING
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


def _row_from_doc(doc: dict[str, Any]) -> tuple | None:
    """Vrátí parametrizovaný tuple pro INSERT, nebo ``None`` pokud doc nelze zpracovat."""
    email = doc.get("user_email")
    exercise = doc.get("exercise_id")
    started = _parse_mongo_date(doc.get("started_at"))
    if not isinstance(email, str) or not isinstance(exercise, str) or started is None:
        return None

    evaluation = doc.get("evaluation")
    return (
        email,
        started.date(),
        exercise,
        started.time(),
        int(doc.get("set_number", 0)),
        int(doc.get("total_reps", 0)),
        doc.get("target_reps"),
        float(doc.get("total_duration_sec", 0.0)),
        Jsonb(doc.get("counting") or []),
        Jsonb(evaluation) if isinstance(evaluation, dict) else None,
        doc.get("user_level"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="load_series_from_mongo_dump",
        description="Backfill workout_series rows from MongoDB exercise_series dump.",
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

    all_rows: list[tuple] = []
    skipped_malformed = 0
    for path in sorted(series_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        row = _row_from_doc(doc)
        if row is None:
            skipped_malformed += 1
            continue
        all_rows.append(row)

    if skipped_malformed:
        print(
            f"  warning: {skipped_malformed} dokumentů přeskočeno (chybí email/exercise/started_at)"
        )

    if not all_rows:
        sys.exit(f"V {series_dir} nejsou žádné použitelné série.")

    with psycopg.connect(database_url, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_email, day FROM workout")
            known_workouts: set[tuple[str, date]] = {(r[0], r[1]) for r in cur.fetchall()}

            valid = [r for r in all_rows if (r[0], r[1]) in known_workouts]
            orphan_keys = sorted(
                {(r[0], r[1]) for r in all_rows if (r[0], r[1]) not in known_workouts}
            )

            if orphan_keys:
                preview = ", ".join(f"{e}@{d}" for e, d in orphan_keys[:5])
                more = f" (+{len(orphan_keys) - 5} dalších)" if len(orphan_keys) > 5 else ""
                skipped_count = len(all_rows) - len(valid)
                print(
                    f"  warning: {skipped_count} řádků přeskočeno kvůli chybějícímu "
                    f"workout: {preview}{more} "
                    f"(nejdřív spusť load_workouts_from_mongo_dump.py)"
                )

            if valid:
                cur.executemany(INSERT_SQL, valid)
        conn.commit()

    written = len(valid)
    skipped = len(all_rows) - written
    total = len(all_rows) + skipped_malformed
    print(
        f"{written} series rows written, {skipped} skipped (no parent workout), "
        f"{total} total docs in {dump_dir.name}"
    )


if __name__ == "__main__":
    main()
