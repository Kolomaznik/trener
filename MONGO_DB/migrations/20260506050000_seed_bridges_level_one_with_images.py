"""Replace `bridges_level_1` YouTube media with two embedded WebP images.

Source images live next to this migration in ``MONGO_DB/images/`` as
1024-px-wide WebP files (converted from the original PNGs). They are read at
module-import time and embedded as ``data:image/webp;base64,...`` strings under
``"img_1"`` and ``"img_2"`` (matching the ``obr. 83`` / ``obr. 84`` callouts
in the source book).

Like ``20260506040000_seed_hspu_level_one_with_images``, this migration
rewrites only the ``media`` field so the markdown description and the absence
of ``instructions`` set by recent migrations are preserved.

``downgrade`` restores the original YouTube-based media from the v1 seed.
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
    "img_1": _data_url_webp("bridges_level_1_1.webp"),
    "img_2": _data_url_webp("bridges_level_1_2.webp"),
}

_OLD_MEDIA = {
    "youtube_tutorial": "https://www.youtube.com/watch?v=8lT2-FzD_G8",
    "thumbnail_url": "https://img.youtube.com/vi/8lT2-FzD_G8/hqdefault.jpg",
}


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_one(
            {"_id": "bridges_level_1"},
            {"$set": {"media": _NEW_MEDIA}},
        )

    def downgrade(self):
        self.db.exercises.update_one(
            {"_id": "bridges_level_1"},
            {"$set": {"media": _OLD_MEDIA}},
        )
