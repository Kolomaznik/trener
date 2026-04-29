"""Trener MongoDB migration runner.

Tenký wrapper kolem knihovny ``mongodb-migrations`` — načte ``.env`` přes
``python-dotenv``, sestaví ``Configuration`` programaticky a deleguje na
``MigrationManager``. Tím obejdeme nejasnosti CLI configu mezi verzemi knihovny
a držíme jediný zdroj pravdy o připojení v ``.env``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pymongo
from dotenv import load_dotenv
from mongodb_migrations.cli import MigrationManager
from mongodb_migrations.config import Configuration, Execution

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
MIGRATIONS_DIR = ROOT / "migrations"


def _load_env() -> tuple[str, str]:
    load_dotenv(ROOT / ".env")
    try:
        uri = os.environ["MONGO_URI"]
        db_name = os.environ["MONGO_DB_NAME"]
    except KeyError as exc:
        sys.exit(f"Chybí proměnná {exc.args[0]} — zkopíruj .env.example do .env a vyplň hodnoty.")

    parsed = urlparse(uri)
    if not parsed.path or parsed.path == "/":
        uri = urlunparse(parsed._replace(path=f"/{db_name}"))
    return uri, db_name


def _build_config(
    uri: str,
    *,
    execution: Execution,
    to_datetime: str | None = None,
) -> Configuration:
    config = Configuration()
    config.mongo_url = uri
    config.mongo_migrations_path = str(MIGRATIONS_DIR)
    config.execution = execution
    config.to_datetime = to_datetime
    return config


def cmd_up(args: argparse.Namespace) -> None:
    uri, _ = _load_env()
    config = _build_config(uri, execution=Execution.MIGRATE, to_datetime=args.to)
    MigrationManager(config).run()


def cmd_down(args: argparse.Namespace) -> None:
    uri, _ = _load_env()
    config = _build_config(uri, execution=Execution.DOWNGRADE, to_datetime=args.to)
    MigrationManager(config).run()


def cmd_status(_args: argparse.Namespace) -> None:
    uri, _ = _load_env()
    client = pymongo.MongoClient(uri)
    db = client.get_default_database()
    metastore = Configuration().metastore
    records = list(db[metastore].find().sort("migration_datetime", pymongo.ASCENDING))
    if not records:
        print("Žádné aplikované migrace.")
        return
    for record in records:
        print(f"{record['migration_datetime']}  applied_at={record.get('created_at')}")


def cmd_new(args: argparse.Namespace) -> None:
    uri, _ = _load_env()
    description = f"{args.category}_{args.description}"
    config = _build_config(uri, execution=Execution.MIGRATE)
    config.description = description
    MigrationManager(config).create_migration()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manage", description="Trener MongoDB migrations")
    sub = parser.add_subparsers(dest="command", required=True)

    p_up = sub.add_parser("up", help="aplikuje pending migrace")
    p_up.add_argument(
        "--to",
        default=None,
        help="aplikovat pouze do tohoto timestampu (YYYYMMDDHHMMSS)",
    )
    p_up.set_defaults(func=cmd_up)

    p_down = sub.add_parser("down", help="rollback applied migrací")
    p_down.add_argument("--to", default=None, help="rollback do tohoto timestampu (exclusive)")
    p_down.set_defaults(func=cmd_down)

    p_status = sub.add_parser("status", help="výpis aplikovaných migrací")
    p_status.set_defaults(func=cmd_status)

    p_new = sub.add_parser("new", help="vytvoří novou migraci se správným timestamp prefixem")
    p_new.add_argument("category", choices=["schema", "seed", "transform"])
    p_new.add_argument("description", help="snake_case popis, pouze [_a-z]")
    p_new.set_defaults(func=cmd_new)

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
