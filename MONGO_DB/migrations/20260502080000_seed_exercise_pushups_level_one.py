from mongodb_migrations.base import BaseMigration

EXERCISE = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "english_name": "Wall Push-ups",
    "family": "Kliky",
    "level": 1,
    "description": (
        "Ideální rehabilitační a přípravný cvik. Buduje základní sílu a zpevňuje "
        "šlachy a klouby horní poloviny těla bez rizika přetížení."
    ),
    "instructions": [
        "Postav se čelem ke zdi, zhruba na vzdálenost natažených paží.",
        "Polož dlaně na zeď na šířku ramen, přesně ve výšce hrudníku.",
        "Zpevni břicho a spodní záda, tělo musí tvořit rovnou osu od hlavy až k patám.",
        "S nádechem pomalu krč lokty a kontrolovaně přibližuj obličej a hrudník ke zdi.",
        "Zastav se v momentě, kdy jsi těsně u zdi, na jednu sekundu pohyb podrž.",
        (
            "S výdechem se plynule odtlač zpět do výchozí pozice, dokud nejsou paže "
            "téměř napnuté (ale nezamykej lokty)."
        ),
        "V horní pozici pohyb na sekundu zastav a opakuj.",
    ],
    "media": {
        "youtube_tutorial": "https://www.youtube.com/watch?v=a6YHbNXW09k",
        "thumbnail_url": "https://img.youtube.com/vi/a6YHbNXW09k/hqdefault.jpg",
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": (
            "Pohyb musí být absolutně plynulý. Rychlé 'odrážení' od zdi neguje účel " "cviku."
        ),
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": (
            "Až zvládneš úroveň mastery s dokonalou kadencí, jsi připraven na úroveň 2 "
            "(Kliky v předklonu)."
        ),
    },
    "muscle_engagement_percent": {
        "chest": 40,
        "triceps": 30,
        "deltoids": 15,
        "abs": 5,
        "lower_back": 5,
        "hands": 5,
    },
}


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_one({"_id": EXERCISE["_id"]}, {"$set": EXERCISE}, upsert=True)

    def downgrade(self):
        self.db.exercises.delete_one({"_id": EXERCISE["_id"]})
