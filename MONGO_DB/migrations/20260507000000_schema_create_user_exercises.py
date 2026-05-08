from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.create_collection("user_exercises")
        self.db.user_exercises.create_index(
            [("user_email", 1), ("exercise_name", 1)],
            unique=True,
        )
        self.db.user_exercises.create_index("user_email")

    def downgrade(self):
        self.db.user_exercises.drop()
