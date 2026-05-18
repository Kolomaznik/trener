"""Rename ``media`` to ``catalog_media`` so the table name reflects what it
holds -- images/clips owned by ``catalog`` exercises. Future per-user
media (e.g. progress photos) would live in a separate ``user_media`` table
without naming collisions.

ASCII only (yoyo opens migrations via plain ``open(path)`` which defaults
to cp1252 on Windows).
"""

from yoyo import step

__depends__: set[str] = {"20260518150000_schema_initial_media"}

steps = [
    step(
        "ALTER TABLE media RENAME TO catalog_media;",
        "ALTER TABLE catalog_media RENAME TO media;",
    ),
]
