"""Initial schema: ``users`` table for Google OAuth + custom profile.

Flat 1:1 mapping over the Mongo ``users`` collection -- no JSONB, only
scalars. PK is ``email`` (canonical join key across other collections),
``sub`` carries ``UNIQUE`` as defense in depth. CHECK constraints mirror
the Pydantic validation in ``BACKEND/app/api/user/settings/patch.py``.

Keep migration file contents ASCII-only: yoyo opens files via plain
``open(path)`` which defaults to cp1252 on Windows and would crash on
multi-byte UTF-8 sequences. Non-ASCII prose belongs in README.md.
"""

from yoyo import step

__depends__: set[str] = set()

steps = [
    step(
        """
        CREATE TABLE users (
            email           TEXT PRIMARY KEY,
            sub             TEXT NOT NULL UNIQUE,
            email_verified  BOOLEAN,
            name            TEXT,
            picture         TEXT,
            birth_year      INT,
            height_cm       INT
                CHECK (height_cm IS NULL OR height_cm BETWEEN 50 AND 250),
            weight_kg       DOUBLE PRECISION
                CHECK (weight_kg IS NULL OR weight_kg BETWEEN 20 AND 300),
            gender          TEXT
                CHECK (gender IS NULL OR gender IN ('male', 'female')),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "DROP TABLE IF EXISTS users;",
    ),
]
