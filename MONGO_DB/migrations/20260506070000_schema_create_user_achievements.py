"""Create the ``user_achievements`` collection.

One document per user holds the Trénink vězně progress matrix
(family -> level -> {stars, achieved_at}). The document is upserted on
first GET to ``/trening-vezne``; this migration only sets up the
collection and the unique index on ``user_email``.
"""

from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.create_collection("user_achievements")
        self.db.user_achievements.create_index("user_email", unique=True)

    def downgrade(self):
        self.db.user_achievements.drop()
