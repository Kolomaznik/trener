"""Update `squats_level_1` with full instructional text and embedded images.

The two reference images live next to this migration in
``MONGO_DB/images/`` as 1024-px-wide WebP files.  They are read at
module-import time and embedded into the document as
``data:image/webp;base64,...`` strings under the keys ``"img_1"`` and
``"img_2"`` (matching the ``obr. 21`` / ``obr. 22`` callouts in
``instructions``).

``downgrade`` restores the v1 content by re-loading the
``squats_level_1`` entry from
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


def _load_v1_squats() -> dict:
    """Re-load the ``squats_level_1`` entry from the batch seed migration."""
    batch_path = _HERE / _BATCH_FILENAME
    spec = importlib.util.spec_from_file_location("_batch_v1", batch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for entry in module.EXERCISES:
        if entry["_id"] == "squats_level_1":
            return entry
    raise RuntimeError("squats_level_1 not found in batch migration")


EXERCISE = {
    "_id": "squats_level_1",
    "id": "squats_level_1",
    "name": "Dřep ve stoji na ramenou",
    "english_name": "Shoulderstand Squats",
    "family": "Dřepy",
    "level": 1,
    "description": (
        "Dřepy ve stoji na ramenou jsou skvělé přípravné cvičení pro každého, kdo "
        "chce s dřepy začít. Vzhledem k obrácené poloze cviku nespočívá na kolenou "
        "a bedrech prakticky žádná váha, což z něj dělá ideální rehabilitační "
        "cvičení pro lidi s poraněnými zády nebo koleny — pomáhá jim vrátit se "
        "zpátky ke sportům, pro které je pohyb nohou důležitý. Technicky vzato "
        "jsou dřepy ve stoji na ramenou náročnější pro horní část těla než pro "
        "spodní. Ale zároveň uvolňují ztuhlé klouby, zvyšují rozsah pohybu, "
        "a především nasměrují začátečníky k dokonalé formě."
    ),
    "instructions": [
        "S ohnutými koleny se položte na záda.",
        "Vykopněte a dostaňte nohy do vzduchu za pomoci rukou.",
        "Když dosáhnete této polohy, podepřete si bedra rukama.",
        (
            "Ramena stále spočívají na zemi. Ocitnete se ve „stoji na ramenou“, "
            "opírat se budete o ramena, horní část zad a o zadní strany paží."
        ),
        "Uvědomte si, že se v těchto místech musíte neustále podpírat a že nesmíte zatěžovat krk.",
        "Vaše tělo musí být rovné, neohýbejte kyčle. To je počáteční poloha (obr. 21).",
        (
            "Udržujte trup rovný, a zároveň se ohněte v kyčlích a kolenou tak, aby "
            "se kolena dotkla čela. To je konečná poloha (obr. 22)."
        ),
        "Natáhněte nohy dozadu tak, aby se trup ocitl v počáteční poloze. Opakujte.",
    ],
    "media": {
        "img_1": _data_url_webp("squats_level_1_1.webp"),
        "img_2": _data_url_webp("squats_level_1_2.webp"),
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": (
            "Na první pokus se každému dotknout se čela koleny nepodaří. Snažte se "
            "je ohýbat co nejvíc a vaše klouby se při každém cvičení uvolní. Tato "
            "technika je prakticky nemožná pro lidi s nadváhou, protože jim překáží "
            "břicho. Než nadbytečná kila shodíte, cvičte raději s prázdným žaludkem."
        ),
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": (
            "Až zvládneš úroveň mastery s dokonalou kadencí, jsi připraven na úroveň "
            "2 (Dřepy s oporou / Jackknife Squats)."
        ),
    },
    "muscle_engagement_percent": {
        "abs": 30,
        "lower_back": 30,
        "quadriceps": 20,
        "hamstrings": 10,
        "knees": 10,
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
        v1_doc = _load_v1_squats()
        self.db.exercises.update_one(
            {"_id": EXERCISE["_id"]},
            {"$set": v1_doc},
            upsert=True,
        )
