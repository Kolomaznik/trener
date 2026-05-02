from mongodb_migrations.base import BaseMigration

DEFAULTS = [
    {"_id": "squat", "name": "Squat", "category": "legs"},
    {"_id": "bench-press", "name": "Bench Press", "category": "chest"},
    {"_id": "deadlift", "name": "Deadlift", "category": "back"},
]


class Migration(BaseMigration):
    def upgrade(self):
        for doc in DEFAULTS:
            self.db.exercises.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)

    def downgrade(self):
        self.db.exercises.delete_many({"_id": {"$in": [doc["_id"] for doc in DEFAULTS]}})
