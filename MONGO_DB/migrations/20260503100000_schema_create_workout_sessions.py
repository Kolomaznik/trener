from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.create_collection("workout_sessions")
        self.db.workout_sessions.create_index([("user_email", 1), ("exercise_id", 1)])
        self.db.workout_sessions.create_index([("user_email", 1), ("started_at", -1)])

    def downgrade(self):
        self.db.workout_sessions.drop()
