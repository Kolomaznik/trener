"""Trener PostgreSQL migration runner.

Tenký wrapper kolem knihovny ``yoyo-migrations`` — načte ``.env`` přes
``python-dotenv``, dohledá migrace v ``migrations/`` a deleguje na yoyo
programatické API. Drží jediný zdroj pravdy o připojení v ``.env`` a stejnou
CLI plochu jako ``MONGO_DB/manage.py`` (up / down / status / new).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from yoyo import get_backend, read_migrations

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
MIGRATIONS_DIR = ROOT / "migrations"

MIGRATION_TEMPLATE = '''"""{description}."""

from yoyo import step

__depends__: set[str] = set()

steps = [
    step(
        """
        -- TODO: forward SQL
        """,
        """
        -- TODO: rollback SQL
        """,
    ),
]
'''


def _load_env() -> str:
    load_dotenv(ROOT / ".env")
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        sys.exit(f"Chybí proměnná {exc.args[0]} — zkopíruj .env.example do .env a vyplň hodnoty.")


def _filter_to(migrations, to_id: str | None):
    """Vrátí podseznam migrací s ``id <= to_id`` (lexikální, timestamp prefix)."""
    if to_id is None:
        return migrations
    return migrations.__class__(m for m in migrations if m.id <= to_id)


def _filter_above(migrations, to_id: str | None):
    """Pro rollback: vrátí migrace s ``id > to_id`` (vše novější, co se má odrolovat)."""
    if to_id is None:
        return migrations
    return migrations.__class__(m for m in migrations if m.id > to_id)


def cmd_up(args: argparse.Namespace) -> None:
    backend = get_backend(_load_env())
    migrations = read_migrations(str(MIGRATIONS_DIR))
    selected = _filter_to(migrations, args.to)
    with backend.lock():
        backend.apply_migrations(backend.to_apply(selected))


def cmd_down(args: argparse.Namespace) -> None:
    backend = get_backend(_load_env())
    migrations = read_migrations(str(MIGRATIONS_DIR))
    selected = _filter_above(migrations, args.to)
    with backend.lock():
        backend.rollback_migrations(backend.to_rollback(selected))


def cmd_status(_args: argparse.Namespace) -> None:
    backend = get_backend(_load_env())
    migrations = read_migrations(str(MIGRATIONS_DIR))
    applied = set(backend.get_applied_migration_hashes())
    if not list(migrations):
        print("Žádné migrace nalezeny.")
        return
    for m in migrations:
        mark = "applied" if m.hash in applied else "pending"
        print(f"  {m.id:<60} {mark}")


def cmd_new(args: argparse.Namespace) -> None:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{args.category}_{args.description}.py"
    target = MIGRATIONS_DIR / filename
    if target.exists():
        sys.exit(f"Soubor už existuje: {target}")
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(
        MIGRATION_TEMPLATE.format(description=f"{args.category}: {args.description}"),
        encoding="utf-8",
    )
    print(f"Vytvořeno: {target.relative_to(ROOT)}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manage", description="Trener PostgreSQL migrations")
    sub = parser.add_subparsers(dest="command", required=True)

    p_up = sub.add_parser("up", help="aplikuje pending migrace")
    p_up.add_argument(
        "--to",
        default=None,
        help="aplikovat pouze do tohoto migration id (YYYYMMDDHHMMSS prefix, inkluzivní)",
    )
    p_up.set_defaults(func=cmd_up)

    p_down = sub.add_parser("down", help="rollback applied migrací")
    p_down.add_argument(
        "--to",
        default=None,
        help="rollback do tohoto migration id (exkluzivní — vše novější se odrolovat)",
    )
    p_down.set_defaults(func=cmd_down)

    p_status = sub.add_parser("status", help="výpis migrací (applied/pending)")
    p_status.set_defaults(func=cmd_status)

    p_new = sub.add_parser("new", help="vytvoří novou migraci se správným timestamp prefixem")
    p_new.add_argument("category", choices=["schema", "seed", "transform"])
    p_new.add_argument("description", help="snake_case popis, pouze [_a-z0-9]")
    p_new.set_defaults(func=cmd_new)

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
