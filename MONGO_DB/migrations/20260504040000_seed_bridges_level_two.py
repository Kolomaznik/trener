"""Seed `bridges_level_2` — *Přímý most* (Straight Bridges).

This is a *new* document (the existing batch seed
``20260502090000_seed_exercises_level_one_batch.py`` only covers
level 1 / Krátké mosty), so ``upgrade`` upserts and ``downgrade``
deletes the row.

Note on ``media``: the YouTube URL below is a placeholder; replace it
once a real tutorial is recorded.  When 1024-px reference images
``bridges_level_2_1.webp`` / ``bridges_level_2_2.webp`` are added to
``MONGO_DB/images/``, swap the ``media`` block to embedded data URLs
in a follow-up migration (same pattern as the v2 seeds for
pushups / squats / pullups / legraises).
"""

from mongodb_migrations.base import BaseMigration

EXERCISE = {
    "_id": "bridges_level_2",
    "id": "bridges_level_2",
    "name": "Přímý most",
    "english_name": "Straight Bridges",
    "family": "Mosty",
    "level": 2,
    "description": (
        "Přímý most vyžaduje, aby se tlakem nohou aktivovaly zádové svaly, rovný "
        "most k tomu potřebuje i tlak rukou, což tento cvik činí obtížnějším. "
        "Takový pohyb nejen tonizuje paže, ale také uvolňuje trup a posiluje "
        "svaly mezi lopatkami, které potřebujete pro to, abyste zvládli další "
        "stupně."
    ),
    "instructions": [
        (
            "Posaďte se na zem, nohy narovnejte před sebe. Kolena musí být rovná, "
            "chodidla jsou od sebe na šířku ramen."
        ),
        ("Položte dlaně na zem poblíž kyčlí tak, aby prsty rukou „mířily“ na prsty na nohou."),
        (
            "Posaďte rovně. Vaše nohy teď svírají pravý úhel s vaším trupem. To je "
            "počáteční poloha (obr. 85)."
        ),
        (
            "Opřete se rukama do země, napněte paže a zároveň zvedejte kyčle "
            "nahoru, dokud nebudou nohy a trup v jedné přímce."
        ),
        (
            "Zvedněte bradu a podívejte se na strop. V této fázi spočívá váha "
            "vašeho těla na dlaních a v patách. To je konečná poloha (obr. 86)."
        ),
        "Udělejte si pauzu a vraťte se zpět.",
        ("Opakujte dle potřeby. Při pohybu nahoru vydechujte, při pohybu dolů se nadechujte."),
    ],
    "media": {
        "youtube_tutorial": "https://www.youtube.com/watch?v=placeholder_straight_bridge",
        "thumbnail_url": ("https://img.youtube.com/vi/placeholder_straight_bridge/hqdefault.jpg"),
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": (
            "Pokud je na vás přímý most příliš těžký, můžete si cvičení usnadnit "
            "zmenšením pákového efektu. Místo provádění techniky s rovnýma nohama "
            "cvičte s ohnutými koleny, jako v krátkém mostě (obr. 84). Pokud je "
            "to pro vás i tak náročné, provádějte cvičení vkleče. Prohněte se "
            "dozadu a stlačte hýždě několik centimetrů k lýtkům. Pokračujte "
            "v tomto částečném pohybu, dokud nezesílíte natolik, že zvládnete "
            "celý pohyb."
        ),
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 20},
        "mastery": {"sets": 3, "reps": 40},
        "coach_note": (
            "Až zvládneš úroveň mastery s dokonalou kadencí, jsi připraven na "
            "úroveň 3 (Úhlový most / Angled Bridges)."
        ),
    },
    "muscle_engagement_percent": {
        "glutes": 30,
        "hamstrings": 25,
        "lower_back": 20,
        "triceps": 15,
        "rhomboids": 10,
    },
}


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_one(
            {"_id": EXERCISE["_id"]},
            {"$set": EXERCISE},
            upsert=True,
        )

    def downgrade(self):
        # New document — rollback removes it cleanly.
        self.db.exercises.delete_one({"_id": EXERCISE["_id"]})
