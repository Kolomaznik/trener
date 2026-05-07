from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.user_exercises.update_many(
            {"consecutive_successes": {"$exists": False}},
            {"$set": {"consecutive_successes": 0}},
        )

    def downgrade(self):
        self.db.user_exercises.update_many({}, {"$unset": {"consecutive_successes": ""}})
