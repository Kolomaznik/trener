"""Update `legraises_level_1` with full instructional text and embedded images.

The two reference images live next to this migration in
``MONGO_DB/images/`` as 1024-px-wide WebP files.  They are read at
module-import time and embedded into the document as
``data:image/webp;base64,...`` strings under the keys ``"img_1"`` and
``"img_2"`` (matching the ``obr. 61`` / ``obr. 62`` callouts in
``instructions``).

``downgrade`` restores the v1 content by re-loading the
``legraises_level_1`` entry from
``20260502090000_seed_exercises_level_one_batch.py`` and re-applying it,
so a rollback puts the document back to the previous shape (no media,
terser description) without losing it entirely.
"""

import base64
import importlib.util
from pathlib import Path

from mongodb_migrations.base import BaseMigration

_HERE = Path(__file__).resolve().parent
_IMAGES_DIR = _HERE.parent / "images"
_BATCH_FILENAME = "20260502090000_seed_exercises_level_one_batch.py"


def _data_url_webp(filename: str) -> str:
    """Encode a WebP from ``MONGO_DB/images/`` as a base64 data URL."""
    raw = (_IMAGES_DIR / filename).read_bytes()
    return f"data:image/webp;base64,{base64.b64encode(raw).decode('ascii')}"


def _load_v1_legraises() -> dict:
    """Re-load the ``legraises_level_1`` entry from the batch seed migration."""
    batch_path = _HERE / _BATCH_FILENAME
    spec = importlib.util.spec_from_file_location("_batch_v1", batch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for entry in module.EXERCISES:
        if entry["_id"] == "legraises_level_1":
            return entry
    raise RuntimeError("legraises_level_1 not found in batch migration")


EXERCISE = {
    "_id": "legraises_level_1",
    "id": "legraises_level_1",
    "name": "Přitahování kolen",
    "english_name": "Knee Tucks",
    "family": "Zdvihy nohou",
    "level": 1,
    "description": (
        "Přitahování kolen je ideálním cvičením pro začátečníky. Vede ke správnému "
        "postavení páteře, trénuje břišní svaly a posiluje přitahovače kyčlí. "
        "Většině lidí také připadá lehké, a tedy představuje skvělou příležitost, "
        "jak obecně zlepšit svou techniku. Důležitý je plynulý pohyb, správný "
        "dechový rytmus a pevně zatažené břicho."
    ),
    "instructions": [
        "Sedněte si na kraj židle nebo postele.",
        "Mírně se zakloňte, uchopte rukama okraj sedadla a narovnejte nohy.",
        (
            "Chodidla jsou spolu s patami několik centimetrů od podlahy. To je "
            "počáteční poloha (obr. 61)."
        ),
        ("Pomalu zvedejte kolena nahoru a k sobě, až budou asi 15-25 cm od " "vašeho hrudníku."),
        "Vydechněte a souběžně přitahujte kolena.",
        (
            "Pohyb ukončíte úplným výdechem, vaše břišní svaly by v té chvíli měly "
            "být pevně stažené. To je konečná poloha (obr. 62)."
        ),
        "Udělejte vteřinovou pauzu a pak se vraťte do počáteční polohy.",
        "Nadechněte se, když natahujete nohy.",
        (
            "Vaše chodidla by měla opsat přímku a neměla by se dotknout podlahy, "
            "dokud cvik neukončíte."
        ),
        "Celou dobu mějte zatažené břicho.",
        (
            "Odolejte nutkání rychle cvik zopakovat, mezi opakováním se musíte "
            "pořádně nadechnout."
        ),
    ],
    "media": {
        "img_1": _data_url_webp("legraises_level_1_1.webp"),
        "img_2": _data_url_webp("legraises_level_1_2.webp"),
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": (
            "Toto cvičení má v počáteční (natažené nohy) i konečné poloze (kolena "
            "přitažená k hrudi) stejnou obtížnost. Aby bylo cvičení trochu snazší, "
            "soustřeďte se na kratší rozsah pohybu. Až váš pas zesílí, postupně "
            "rozsah pohybu zvětšujte, dokud nebude provedení dokonalé."
        ),
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 40},
        "coach_note": (
            "Až zvládneš úroveň mastery s dokonalou kadencí, jsi připraven na "
            "úroveň 2 (Zdvihy nohou vleže / Flat Knee Raises)."
        ),
    },
    "muscle_engagement_percent": {
        "abs": 45,
        "hip_flexors": 45,
        "quadriceps": 10,
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
        v1_doc = _load_v1_legraises()
        self.db.exercises.update_one(
            {"_id": EXERCISE["_id"]},
            {"$set": v1_doc},
            upsert=True,
        )
