"""Replace ``exercises.completed`` (boolean) with ``exercises.completed_at``
(DATE), and demote ``created_at`` from TIMESTAMPTZ to DATE.

Semantic shift: ``completed_at IS NULL`` -> not done yet; otherwise the
date the user marked it done. Per-second granularity for either column
isn't needed for the workout flow -- one row per (user, exercise) per
day is the natural unit.

The TIMESTAMPTZ -> DATE cast uses the session timezone (Postgres default
is UTC); existing rows shift into their UTC-day buckets. Acceptable for
dev. Rollback re-adds ``completed`` as BOOLEAN DEFAULT FALSE -- any
``completed_at`` info is lost.

ASCII only (yoyo opens migrations via plain ``open(path)`` which defaults
to cp1252 on Windows).
"""

from yoyo import step

__depends__: set[str] = {"20260518160000_schema_rename_media_to_catalog_media"}

steps = [
    step(
        """
        ALTER TABLE exercises
            DROP COLUMN completed,
            ADD COLUMN completed_at DATE,
            ALTER COLUMN created_at DROP DEFAULT,
            ALTER COLUMN created_at TYPE DATE USING created_at::date,
            ALTER COLUMN created_at SET DEFAULT CURRENT_DATE;
        """,
        """
        ALTER TABLE exercises
            ALTER COLUMN created_at DROP DEFAULT,
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::timestamptz,
            ALTER COLUMN created_at SET DEFAULT now(),
            DROP COLUMN completed_at,
            ADD COLUMN completed BOOLEAN NOT NULL DEFAULT FALSE;
        """,
    ),
]
