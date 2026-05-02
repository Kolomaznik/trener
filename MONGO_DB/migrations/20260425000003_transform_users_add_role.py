from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.users.update_many(
            {"role": {"$exists": False}},
            {"$set": {"role": "user"}},
        )

    def downgrade(self):
        self.db.users.update_many(
            {"role": "user"},
            {"$unset": {"role": ""}},
        )
