"""Restore MongoDB databáze ze stromu JSON souborů vytvořeného ``dump.py``.

Načte připojení z ``.env`` (stejně jako ``manage.py``), vybere dump z adresáře
``dumps/`` a nahraje dokumenty zpět do databáze.

Výběr dumpu:

* ``--latest`` — bez ptaní vezme nejnovější dump
* jinak vypíše nalezené dumpy a nechá uživatele vybrat (default = nejnovější)

S ``--clean`` se před nahráním zahodí všechny kolekce v cílové databázi.
Bez ní se dokumenty upsertují podle ``_id`` (existující se přepíšou).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pymongo
from bson.json_util import loads as bson_loads
from dotenv import load_dotenv

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DUMPS_DIR = ROOT / "dumps"


def _load_env() -> tuple[str, str]:
    load_dotenv(ROOT / ".env")
    try:
        uri = os.environ["MONGO_URI"]
        db_name = os.environ["MONGO_DB_NAME"]
    except KeyError as exc:
        sys.exit(f"Chybí proměnná {exc.args[0]} — zkopíruj .env.example do .env a vyplň hodnoty.")

    return uri, db_name


def _find_dumps() -> list[Path]:
    """Adresáře dumpů, seřazené od nejstaršího po nejnovější.

    Názvy jsou ``YYYY-MM-DD_HHMMSS``, takže lexikální řazení = chronologické.
    """
    if not DUMPS_DIR.is_dir():
        sys.exit(f"Adresář {DUMPS_DIR} neexistuje — nejdřív spusť dump.py.")
    dumps = sorted(p for p in DUMPS_DIR.iterdir() if p.is_dir())
    if not dumps:
        sys.exit(f"V {DUMPS_DIR} nejsou žádné dumpy.")
    return dumps


def _select_dump(use_latest: bool) -> Path:
    dumps = _find_dumps()
    latest = dumps[-1]
    if use_latest:
        return latest

    print("Dostupné dumpy:")
    for idx, path in enumerate(dumps, start=1):
        marker = "  (nejnovější)" if path is latest else ""
        print(f"  {idx}. {path.name}{marker}")

    choice = input(f"Vyber dump [1-{len(dumps)}, Enter = nejnovější]: ").strip()
    if not choice:
        return latest
    try:
        index = int(choice)
        if not 1 <= index <= len(dumps):
            raise ValueError
    except ValueError:
        sys.exit(f"Neplatná volba: {choice!r}")
    return dumps[index - 1]


def main() -> None:
    parser = argparse.ArgumentParser(prog="restore", description="Restore MongoDB z JSON dumpu")
    parser.add_argument("--latest", action="store_true", help="vezmi nejnovější dump bez ptaní")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="před nahráním zahoď všechny kolekce v cílové databázi",
    )
    args = parser.parse_args()

    uri, db_name = _load_env()
    dump_dir = _select_dump(args.latest)

    client = pymongo.MongoClient(uri)
    db = client[db_name]

    print(f"Restore '{dump_dir.name}' -> databáze '{db.name}'")

    if args.clean:
        for collection_name in db.list_collection_names():
            db[collection_name].drop()
        print(f"  databáze vyčištěna ({db.name})")

    total = 0
    for coll_dir in sorted(p for p in dump_dir.iterdir() if p.is_dir()):
        collection = db[coll_dir.name]
        count = 0
        for path in sorted(coll_dir.glob("*.json")):
            record = bson_loads(path.read_text(encoding="utf-8"))
            collection.replace_one({"_id": record["_id"]}, record, upsert=True)
            count += 1

        print(f"  {coll_dir.name}: {count} záznamů")
        total += count

    print(f"Hotovo — {total} záznamů.")


if __name__ == "__main__":
    main()
