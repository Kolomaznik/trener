"""Initial schema and seed for the trener app (post-refactor consolidation).

This is the single migration that bootstraps a fresh database. All earlier
migrations were collapsed into this one when the project moved to the v2
data model (per-user state in ``user_exercises`` with ``level_history``,
no catalog copies, no per-session snapshots).

Collections created
-------------------
* ``users``            — Google profile + height/weight. Unique index on email.
* ``exercises``        — Immutable system catalog. Seeded from
                         ``seed/exercises.json``.
* ``user_exercises``   — Per-user state. Composite unique index on
                         (user_email, exercise_name).
* ``workout_sessions`` — One document per finished set. Indexed by
                         (user_email, exercise_id) and (user_email, started_at desc).
* ``user_achievements`` — Trénink vězně cells matrix. Unique index on user_email.

Seed data
---------
If a ``seed/exercises.json`` file sits next to the migrations directory,
its documents are inserted verbatim into ``exercises`` (idempotently —
existing ``_id``s are skipped). When the file is absent, this migration
just creates the collections + indexes; the catalog can be populated
later by any other means.
"""

from __future__ import annotations

import json
from pathlib import Path

from mongodb_migrations.base import BaseMigration

_SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "exercises.json"


class Migration(BaseMigration):
    def upgrade(self):
        # ── users ────────────────────────────────────────────────────────────
        if "users" not in self.db.list_collection_names():
            self.db.create_collection("users")
        self.db.users.create_index("email", unique=True)

        # ── exercises ────────────────────────────────────────────────────────
        if "exercises" not in self.db.list_collection_names():
            self.db.create_collection("exercises")
        self.db.exercises.create_index("name", unique=True)
        self.db.exercises.create_index([("family", 1), ("level", 1)])

        if _SEED_FILE.is_file():
            with _SEED_FILE.open("r", encoding="utf-8") as fh:
                exercises = json.load(fh)
            if exercises:
                # Idempotent seed: skip docs whose _id already exists so reruns
                # against a partially-populated DB don't fail on duplicate keys.
                existing_ids = {
                    doc["_id"]
                    for doc in self.db.exercises.find(
                        {"_id": {"$in": [d["_id"] for d in exercises]}},
                        {"_id": 1},
                    )
                }
                new_docs = [d for d in exercises if d["_id"] not in existing_ids]
                if new_docs:
                    self.db.exercises.insert_many(new_docs)

        # ── user_exercises (v2: no catalog copies, with level_history) ───────
        if "user_exercises" not in self.db.list_collection_names():
            self.db.create_collection("user_exercises")
        self.db.user_exercises.create_index(
            [("user_email", 1), ("exercise_name", 1)],
            unique=True,
        )
        self.db.user_exercises.create_index("user_email")

        # ── workout_sessions (v2: no snapshot fields) ────────────────────────
        if "workout_sessions" not in self.db.list_collection_names():
            self.db.create_collection("workout_sessions")
        self.db.workout_sessions.create_index([("user_email", 1), ("exercise_id", 1)])
        self.db.workout_sessions.create_index([("user_email", 1), ("started_at", -1)])

        # ── user_achievements (Trénink vězně cells matrix) ──────────────────
        if "user_achievements" not in self.db.list_collection_names():
            self.db.create_collection("user_achievements")
        self.db.user_achievements.create_index("user_email", unique=True)

    def downgrade(self):
        for name in (
            "user_achievements",
            "workout_sessions",
            "user_exercises",
            "exercises",
            "users",
        ):
            if name in self.db.list_collection_names():
                self.db.drop_collection(name)
