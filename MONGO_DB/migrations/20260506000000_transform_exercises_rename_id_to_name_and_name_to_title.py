"""Rename exercise fields: id → name, name → title.

Step 1 of a multi-step refactor. _id stays as the MongoDB internal id;
the slug (formerly id) becomes name, and the human-readable label
(formerly name) becomes title.
"""

from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_many(
            {"id": {"$exists": True}},
            [
                {"$set": {"title": "$name", "name": "$id"}},
                {"$unset": "id"},
            ],
        )

    def downgrade(self):
        self.db.exercises.update_many(
            {"title": {"$exists": True}},
            [
                {"$set": {"id": "$name", "name": "$title"}},
                {"$unset": "title"},
            ],
        )
