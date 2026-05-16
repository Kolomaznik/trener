"""Dump celé MongoDB databáze do stromu JSON souborů.

Načte připojení z ``.env`` (stejně jako ``manage.py``) a uloží každý dokument
jako samostatný JSON soubor ve struktuře::

    dumps/<YYYY-MM-DD_HHMMSS>/<collection_name>/<record_id>.json

Serializace jde přes ``bson.json_util``, takže typy specifické pro BSON
(``ObjectId``, ``datetime`` …) zůstanou zachované v Extended JSON formátu.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pymongo
from bson.json_util import dumps as bson_dumps
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


def _safe_filename(record_id: object) -> str:
    """Záznamové ID na bezpečný název souboru (ObjectId i ostatní typy)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(record_id))


def main() -> None:
    uri, db_name = _load_env()
    client = pymongo.MongoClient(uri)
    db = client[db_name]

    target = DUMPS_DIR / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Dump databáze '{db.name}' -> {target}")

    total = 0
    for collection_name in sorted(db.list_collection_names()):
        coll_dir = target / collection_name
        coll_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for record in db[collection_name].find():
            path = coll_dir / f"{_safe_filename(record['_id'])}.json"
            path.write_text(bson_dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            count += 1

        print(f"  {collection_name}: {count} záznamů")
        total += count

    print(f"Hotovo — {total} záznamů.")


if __name__ == "__main__":
    main()
