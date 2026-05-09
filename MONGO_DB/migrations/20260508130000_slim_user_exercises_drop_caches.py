"""Drop derived-cache fields from existing ``user_exercises`` rows.

After the v2 schema slim-down, ``user_exercises`` stores only intrinsic
per-user state. Catalog and session-derived values are computed at
read time by the endpoints that serve them.

Removed fields::

    target_reps, target_sets, rest_seconds,
    best_result, recent_sets, muscle_load_by_difficulty,
    updated_at, completed_at

Existing documents predating this slim-down are reshaped via ``$unset``;
no row is dropped or duplicated. ``downgrade`` is a no-op because the
removed values are derivable on demand — there is nothing to put back.
"""

from mongodb_migrations.base import BaseMigration

_DROPPED_FIELDS = {
    "target_reps": "",
    "target_sets": "",
    "rest_seconds": "",
    "best_result": "",
    "recent_sets": "",
    "muscle_load_by_difficulty": "",
    "updated_at": "",
    "completed_at": "",
}


class Migration(BaseMigration):
    def upgrade(self):
        if "user_exercises" not in self.db.list_collection_names():
            return
        self.db.user_exercises.update_many({}, {"$unset": _DROPPED_FIELDS})

    def downgrade(self):
        # Nothing to restore — every removed field is recomputable from
        # the catalog, workout_sessions, or REST_SECONDS / level_history.
        pass
