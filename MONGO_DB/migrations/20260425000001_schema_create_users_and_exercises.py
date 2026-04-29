from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.create_collection("users")
        self.db.create_collection("exercises")
        self.db.users.create_index("email", unique=True)
        self.db.exercises.create_index([("category", 1), ("name", 1)])

    def downgrade(self):
        self.db.users.drop()
        self.db.exercises.drop()
