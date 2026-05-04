"""Update `pushups_level_1` with full instructional text and embedded images.

The two reference images live next to this migration in
``MONGO_DB/images/`` as 1024-px-wide WebP files.  They are read at
module-import time and embedded into the document as
``data:image/webp;base64,...`` strings under the keys ``"img_1"`` and
``"img_2"`` (matching the ``obr. 1`` / ``obr. 2`` callouts in
``instructions``).

``downgrade`` restores the v1 content by re-loading
``20260502080000_seed_exercise_pushups_level_one.py`` and re-applying its
``EXERCISE`` dict, so a rollback puts the document back to the previous
shape (YouTube media, terser description) without losing it entirely.
"""

import base64
import importlib.util
from pathlib import Path

from mongodb_migrations.base import BaseMigration

_HERE = Path(__file__).resolve().parent
_IMAGES_DIR = _HERE.parent / "images"
_V1_FILENAME = "20260502080000_seed_exercise_pushups_level_one.py"


def _data_url_webp(filename: str) -> str:
    """Encode a WebP from ``MONGO_DB/images/`` as a base64 data URL."""
    raw = (_IMAGES_DIR / filename).read_bytes()
    return f"data:image/webp;base64,{base64.b64encode(raw).decode('ascii')}"


def _load_v1_exercise() -> dict:
    """Re-load the v1 EXERCISE dict so ``downgrade`` can restore it."""
    v1_path = _HERE / _V1_FILENAME
    spec = importlib.util.spec_from_file_location("_pushups_v1", v1_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.EXERCISE


EXERCISE = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "english_name": "Wall Push-ups",
    "family": "Kliky",
    "level": 1,
    "description": (
        "Kliky o zeď jsou první ze série deseti cviků, potřebných k dokonalému "
        "zvládnutí kliků. Je to první stupeň, a proto je nejjednodušší. Každý zdravý "
        "člověk by měl dokázat provést tento cvik bez jakýchkoli problémů. Kliky o "
        "zeď také patří do terapeutické série kliků, užitečných pro každého, kdo se "
        "zotavuje po úraze nebo po operaci a snaží se uzdravit a pomalu obnovit svou "
        "sílu. K chronickým a akutním úrazům jsou náchylné především lokty, zápěstí "
        "a ramena, zejména citlivé rotátorové manžety v rameni. Toto cvičení dané "
        "oblasti jemně aktivuje, stimuluje, zlepšuje jejich prokrvení a svalový "
        "tonus. Začátečníci musí vždy začínat velmi citlivě, aby dali svým "
        "schopnostem možnost se rozvíjet co nejpřirozeněji. Proto by měli začít "
        "s tímto cvičením."
    ),
    "instructions": [
        "Postavte se proti zdi, chodidla mějte u sebe.",
        "Položte dlaně naplocho na zeď. To je počáteční poloha (obr. 1).",
        "Ruce jsou rovné a roztažené na šířku ramene, dlaně jsou ve výšce prsou.",
        "Ohněte ramena a lokty, dokud se čelo jemně nedotkne zdi.",
        "To je konečná poloha (obr. 2).",
        "Dostaňte se zpět do počáteční polohy a opakujte.",
    ],
    "media": {
        "img_1": _data_url_webp("pushups_level_1_1.webp"),
        "img_2": _data_url_webp("pushups_level_1_2.webp"),
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": (
            "Každý, kdo čte tuto knihu, by měl být schopný provést toto cvičení, "
            "pokud není tělesně postižený, těžce zraněný nebo nemocný. Pokud se "
            "zotavujeme po úraze nebo operaci, tento pohyb je dobrým testem možných "
            "slabin, které mohou během rehabilitace způsobit problémy."
        ),
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": (
            "Až zvládneš úroveň mastery s dokonalou kadencí, jsi připraven na úroveň "
            "2 (Kliky v předklonu)."
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
        self.db.exercises.update_one(
            {"_id": EXERCISE["_id"]},
            {"$set": EXERCISE},
            upsert=True,
        )

    def downgrade(self):
        # Restore the v1 content by re-applying the previous seed.
        v1_doc = _load_v1_exercise()
        self.db.exercises.update_one(
            {"_id": EXERCISE["_id"]},
            {"$set": v1_doc},
            upsert=True,
        )
