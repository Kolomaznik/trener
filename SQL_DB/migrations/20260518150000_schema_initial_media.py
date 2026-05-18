"""Initial schema: ``media`` table -- one row per exercise image/clip.

Replaces the previous ``catalog.media`` JSONB blob. Composite PK is
``(exercise_name, name)``: ``exercise_name`` references ``catalog(name)``
with ON DELETE CASCADE so removing an exercise wipes its media; ``name``
is the media slot (e.g. "front", "back", "demo"). ``data`` holds the
full ``data:image/...;base64,...`` URI verbatim.

ASCII only (yoyo opens migrations via plain ``open(path)`` which defaults
to cp1252 on Windows).
"""

from yoyo import step

__depends__: set[str] = {"20260516120000_schema_initial_catalog"}

steps = [
    step(
        """
        CREATE TABLE media (
            exercise_name TEXT NOT NULL REFERENCES catalog(name) ON DELETE CASCADE,
            name          TEXT NOT NULL,
            data          TEXT NOT NULL,
            PRIMARY KEY (exercise_name, name)
        );
        """,
        "DROP TABLE IF EXISTS media;",
    ),
]
