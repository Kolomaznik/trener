"""Initial schema: ``catalog`` table for exercise definitions.

Hybrid shape — scalar columns for the small queryable fields, JSONB for
``cadence`` and ``media``, and one INT column per muscle (default 0) from
the frontend canonical muscle map. Future muscles → ALTER TABLE migration.
"""

from yoyo import step

__depends__: set[str] = set()

steps = [
    step(
        """
        CREATE TABLE catalog (
            name          TEXT PRIMARY KEY,
            title         TEXT NOT NULL,
            english_name  TEXT,
            description   TEXT NOT NULL,
            cadence       JSONB NOT NULL,
            media         JSONB NOT NULL DEFAULT '{}'::jsonb,

            chest         INT NOT NULL DEFAULT 0,
            deltoids      INT NOT NULL DEFAULT 0,
            biceps        INT NOT NULL DEFAULT 0,
            triceps       INT NOT NULL DEFAULT 0,
            forearms      INT NOT NULL DEFAULT 0,
            abs           INT NOT NULL DEFAULT 0,
            obliques      INT NOT NULL DEFAULT 0,
            hip_flexors   INT NOT NULL DEFAULT 0,
            trapezius     INT NOT NULL DEFAULT 0,
            rhomboids     INT NOT NULL DEFAULT 0,
            lats          INT NOT NULL DEFAULT 0,
            lower_back    INT NOT NULL DEFAULT 0,
            quadriceps    INT NOT NULL DEFAULT 0,
            hamstrings    INT NOT NULL DEFAULT 0,
            glutes        INT NOT NULL DEFAULT 0,
            abductors     INT NOT NULL DEFAULT 0,
            adductors     INT NOT NULL DEFAULT 0,
            calves        INT NOT NULL DEFAULT 0,
            tibialis      INT NOT NULL DEFAULT 0,
            neck          INT NOT NULL DEFAULT 0,
            knees         INT NOT NULL DEFAULT 0,
            hands         INT NOT NULL DEFAULT 0,
            ankles        INT NOT NULL DEFAULT 0,
            feet          INT NOT NULL DEFAULT 0
        );
        """,
        "DROP TABLE IF EXISTS catalog;",
    ),
]
