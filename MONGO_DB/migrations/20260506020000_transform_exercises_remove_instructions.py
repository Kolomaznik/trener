"""Remove the ``instructions`` field from all exercise documents.

The technique steps that lived in ``instructions`` are now part of the
markdown ``description`` field (the ``## Provedení`` section).

Downgrade is a no-op: this migration discards data, and the original
``instructions`` arrays only exist inside historical seed migrations. If you
need them back, re-run the relevant seed migration manually.
"""

from mongodb_migrations.base import BaseMigration


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_many(
            {"instructions": {"$exists": True}},
            {"$unset": {"instructions": ""}},
        )

    def downgrade(self):
        pass
