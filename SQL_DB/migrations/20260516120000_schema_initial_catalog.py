"""Initial schema: ``catalog`` table for exercise definitions.

Scalar columns for the small queryable fields, JSONB for the variable
ones: ``goal`` (target sets x reps) and ``muscle_engagement`` (free-form
``{muscle_name: percent}`` dict -- adding a new muscle does not require
a schema migration).

``goal`` collapses what Mongo stored as a three-tier
``progression_goals`` object into a single ``{sets, reps}`` target; the
seed loader picks ``reps`` from the intermediate tier and ``sets`` from
mastery.

Media (images/clips) lives in a sibling ``media`` table -- one row per
image -- so the per-exercise base64 blobs don't bloat ``SELECT *`` on
catalog. See ``20260518150000_schema_initial_media.py``.
"""

from yoyo import step

__depends__: set[str] = set()

steps = [
    step(
        """
        CREATE TABLE catalog (
            name               TEXT PRIMARY KEY,
            title              TEXT NOT NULL,
            english_name       TEXT,
            description        TEXT NOT NULL,
            goal               JSONB NOT NULL DEFAULT '{}'::jsonb,
            muscle_engagement  JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """,
        "DROP TABLE IF EXISTS catalog;",
    ),
]
