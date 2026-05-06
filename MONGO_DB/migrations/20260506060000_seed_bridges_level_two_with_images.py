"""Replace `bridges_level_2` placeholder media with two embedded WebP images.

Source images live next to this migration in ``MONGO_DB/images/`` as
1024-px-wide WebP files. They are read at module-import time and embedded
as ``data:image/webp;base64,...`` strings under ``"img_1"`` and ``"img_2"``
(matching the ``obr. 85`` / ``obr. 86`` callouts in the source book).

Same shape as ``20260506040000_seed_hspu_level_one_with_images`` — rewrites
only the ``media`` field. Downgrade restores the placeholder YouTube media
from the v1 seed.
"""

import base64
from pathlib import Path

from mongodb_migrations.base import BaseMigration

_HERE = Path(__file__).resolve().parent
_IMAGES_DIR = _HERE.parent / "images"


def _data_url_webp(filename: str) -> str:
    raw = (_IMAGES_DIR / filename).read_bytes()
    return f"data:image/webp;base64,{base64.b64encode(raw).decode('ascii')}"


_NEW_MEDIA = {
    "img_1": _data_url_webp("bridges_level_2_1.webp"),
    "img_2": _data_url_webp("bridges_level_2_2.webp"),
}

_OLD_MEDIA = {
    "youtube_tutorial": "https://www.youtube.com/watch?v=placeholder_straight_bridge",
    "thumbnail_url": "https://img.youtube.com/vi/placeholder_straight_bridge/hqdefault.jpg",
}


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_one(
            {"_id": "bridges_level_2"},
            {"$set": {"media": _NEW_MEDIA}},
        )

    def downgrade(self):
        self.db.exercises.update_one(
            {"_id": "bridges_level_2"},
            {"$set": {"media": _OLD_MEDIA}},
        )
