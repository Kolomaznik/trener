"""Initial schema: ``workout`` -- one row per (user, day) prescription.

Each row holds a snapshot of the user's active exercises at the moment
the row was created. ``plan`` is a JSONB array of ``exercise_name``
strings -- no FK on individual array elements; integrity is enforced
indirectly at INSERT time by sourcing from ``exercises`` (which itself
FKs into ``catalog``).

Stored as JSONB (not TEXT[]) so future per-exercise overrides --
custom sets/reps for a single day -- can drop in without ALTER TABLE.
Today the array is just plain strings.

ASCII only (yoyo opens migrations via plain ``open(path)`` which defaults
to cp1252 on Windows).
"""

from yoyo import step

__depends__: set[str] = {"20260518170000_schema_exercises_completed_at"}

steps = [
    step(
        """
        CREATE TABLE workout (
            user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            day        DATE NOT NULL,
            plan       JSONB NOT NULL DEFAULT '[]'::jsonb,
            PRIMARY KEY (user_email, day)
        );
        """,
        "DROP TABLE IF EXISTS workout;",
    ),
]
