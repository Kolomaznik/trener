"""Initial schema: ``workout_series`` -- one row per set the user logged.

Child of ``workout``: every series belongs to one workout (composite FK on
``(user_email, day)``). ``exercise_name`` is a direct FK to ``catalog(name)``
so series can only reference real exercises.

PK is ``(user_email, day, exercise_name, time)`` -- ``time`` (TIME WITHOUT
TIME ZONE, microsecond precision) discriminates between sets of the same
exercise on the same day. The date lives on the parent workout row, so we
only need the wall-clock time here.

``counting`` (array of per-rep events) and ``evaluation`` (pace/trend/
recommendation object) stay JSONB -- they're shape-stable enough not to
need their own tables, but variable enough that splitting columns would
be tedious.

ASCII only (yoyo opens migrations via plain ``open(path)`` which defaults
to cp1252 on Windows).
"""

from yoyo import step

__depends__: set[str] = {"20260518180000_schema_initial_workout"}

steps = [
    step(
        """
        CREATE TABLE workout_series (
            user_email         TEXT NOT NULL,
            day                DATE NOT NULL,
            exercise_name      TEXT NOT NULL REFERENCES catalog(name) ON DELETE CASCADE,
            time               TIME NOT NULL,
            set_number         INT  NOT NULL,
            total_reps         INT  NOT NULL,
            target_reps        INT,
            total_duration_sec DOUBLE PRECISION NOT NULL,
            counting           JSONB NOT NULL DEFAULT '[]'::jsonb,
            evaluation         JSONB,
            user_level         TEXT,
            PRIMARY KEY (user_email, day, exercise_name, time),
            FOREIGN KEY (user_email, day) REFERENCES workout(user_email, day) ON DELETE CASCADE
        );
        """,
        "DROP TABLE IF EXISTS workout_series;",
    ),
]
