from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    INDEX_NAME = "users_email_unique"

    def _has_unique_email_index(self) -> bool:
        for spec in self.db.users.index_information().values():
            if spec.get("unique") and spec.get("key") == [("email", 1)]:
                return True
        return False

    def upgrade(self):
        if self._has_unique_email_index():
            return
        self.db.users.create_index("email", unique=True, name=self.INDEX_NAME)

    def downgrade(self):
        if self.INDEX_NAME in self.db.users.index_information():
            self.db.users.drop_index(self.INDEX_NAME)
