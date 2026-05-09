"""Rename ``workout_sessions`` → ``exercise_series``.

The collection's document shape is unchanged; only the name and the
collection-level indexes get a new home. ``renameCollection`` is atomic
on a single MongoDB server, so existing documents flip over without a
data migration.

Idempotent: if the rename has already been applied, this no-ops. If
neither collection exists yet (e.g. the consolidated initial migration
ran on a fresh DB and used the old name), this still lands a usable
``exercise_series`` collection.

Note: the new POST /exercise-series endpoint also persists ``evaluation``
and ``target_reps`` on each series doc. This migration leaves *existing*
rows alone — they simply won't have those fields. New rows written
after this migration carry the full v2 shape.
"""

from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        names = self.db.list_collection_names()
        if "exercise_series" not in names:
            if "workout_sessions" in names:
                self.db.workout_sessions.rename("exercise_series")
            else:
                self.db.create_collection("exercise_series")

        self.db.exercise_series.create_index(
            [("user_email", 1), ("exercise_id", 1), ("started_at", -1)]
        )
        self.db.exercise_series.create_index([("user_email", 1), ("started_at", -1)])

    def downgrade(self):
        names = self.db.list_collection_names()
        if "exercise_series" in names and "workout_sessions" not in names:
            self.db.exercise_series.rename("workout_sessions")
