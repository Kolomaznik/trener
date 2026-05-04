"""Update `pullups_level_1` with full instructional text and embedded images.

The two reference images live next to this migration in
``MONGO_DB/images/`` as 1024-px-wide WebP files.  They are read at
module-import time and embedded into the document as
``data:image/webp;base64,...`` strings under the keys ``"img_1"`` and
``"img_2"`` (matching the ``obr. 41`` / ``obr. 42`` callouts in
``instructions``).

``downgrade`` restores the v1 content by re-loading the
``pullups_level_1`` entry from
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


def _load_v1_pullups() -> dict:
    """Re-load the ``pullups_level_1`` entry from the batch seed migration."""
    batch_path = _HERE / _BATCH_FILENAME
    spec = importlib.util.spec_from_file_location("_batch_v1", batch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for entry in module.EXERCISES:
        if entry["_id"] == "pullups_level_1":
            return entry
    raise RuntimeError("pullups_level_1 not found in batch migration")


EXERCISE = {
    "_id": "pullups_level_1",
    "id": "pullups_level_1",
    "name": "Vertikální shyb",
    "english_name": "Vertical Pulls",
    "family": "Shyby",
    "level": 1,
    "description": (
        "Vertikální shyb je velmi jemný cvik, ideální pro sportovce, kteří se "
        "pokouší obnovit sílu svých zad a paží po nějakém zranění, například "
        "ramene, bicepsu nebo lokte. Zvyšuje průtok krve a obnovuje dřívější "
        "úroveň protažení. Je to také skvělé cvičení pro jakéhokoliv "
        "začátečníka. Malá intenzita umožňuje sportovcům, kteří začínají se "
        "shyby, aby přišli na to, že v ramenou a horní části zad opravdu mají "
        "svaly."
    ),
    "instructions": [
        "Najděte si nějakou vertikální základnu, na které se dokážete udržet.",
        (
            "Měla by být bezpečná a umožnit vám pohodlný úchop, takže navrhuji "
            "dveřní rám nebo vysoké zábradlí."
        ),
        ("Postavte se blízko základny, špičky vašich chodidel by měly být 7 až " "15 cm daleko."),
        "Uchopte základnu tak, aby vám to bylo pohodlné.",
        (
            "Ideálně by vaše ruce měly být na šířku ramen od sebe, ale stačí, když "
            "budete stát tak, aby to bylo symetrické. Toto je počáteční poloha "
            "(obr. 41)."
        ),
        "Díky blízkosti základny budou vaše paže ohnuté.",
        ("Teď nechte váhu vašeho těla, aby se za pomoci mírného „opření“ " "posunula dozadu."),
        (
            "Přitom roztahujte paže tak, aby na konci byly téměř rovné a vaše "
            "tělo směřovalo uhlopříčně dozadu. Toto je konečná poloha (obr. 42)."
        ),
        "V tomto bodě budete cítit mírný tah v horní části zad a možná i v pažích.",
        "Udělejte krátkou pauzu, než se přitáhnete zpět do počáteční polohy.",
        "To provedete stažením lopatek, paže nechte lehce ohnuté.",
        "Na chvíli si odpočiňte a cvik opakujte.",
    ],
    "media": {
        "img_1": _data_url_webp("pullups_level_1_1.webp"),
        "img_2": _data_url_webp("pullups_level_1_2.webp"),
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": (
            "Toto by mělo být snadné cvičení, které by měl zvládnout doslova "
            "každý. Pokud se rehabilitujete po nějakém zranění a pohyb v dané "
            "oblasti (kde máte možná ještě stehy) se vám zdá příliš prudký, "
            "jednoduše omezte rozsah pohybu, zpevněte ramena a nenatahujte paže "
            "tak daleko."
        ),
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 20},
        "mastery": {"sets": 3, "reps": 40},
        "coach_note": (
            "Až zvládneš úroveň mastery s dokonalou kadencí, jsi připraven na "
            "úroveň 2 (Horizontální přítahy)."
        ),
    },
    "muscle_engagement_percent": {
        "lats": 30,
        "rhomboids": 25,
        "biceps": 20,
        "forearms": 15,
        "hands": 10,
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
        v1_doc = _load_v1_pullups()
        self.db.exercises.update_one(
            {"_id": EXERCISE["_id"]},
            {"$set": v1_doc},
            upsert=True,
        )
