"""Initial schema: ``exercises`` table -- per-user x catalog join.

N:M between ``users`` (by email) and ``catalog`` (by name) with a
composite primary key ``(exercise_name, user_email)``. Stores only the
minimal intrinsic per-user state right now: ``completed`` and
``created_at`` (when the user added the exercise). Mongo's per-user
state-machine fields (``user_level``, ``consecutive_successes``,
``level_history``) are intentionally deferred to a follow-up migration.

ON DELETE CASCADE on both FKs: removing a user or a catalog entry drops
the dangling per-user rows.

Keep migration file contents ASCII-only -- yoyo opens files via plain
``open(path)`` which defaults to cp1252 on Windows and would crash on
multi-byte UTF-8 sequences.
"""

from yoyo import step

__depends__: set[str] = set()

steps = [
    step(
        """
        CREATE TABLE exercises (
            exercise_name  TEXT NOT NULL REFERENCES catalog(name) ON DELETE CASCADE,
            user_email     TEXT NOT NULL REFERENCES users(email)  ON DELETE CASCADE,
            completed      BOOLEAN NOT NULL DEFAULT FALSE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (exercise_name, user_email)
        );
        CREATE INDEX exercises_user_email_idx ON exercises(user_email);
        """,
        "DROP TABLE IF EXISTS exercises;",
    ),
]
