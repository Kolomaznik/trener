"""Replace `hspu_level_1` YouTube media with two embedded WebP images.

Source images live next to this migration in ``MONGO_DB/images/`` as
1024-px-wide WebP files (converted from the original PNGs). They are read at
module-import time and embedded as ``data:image/webp;base64,...`` strings under
``"img_1"`` and ``"img_2"`` (matching the ``obr. 107`` / ``obr. 108`` callouts
in the source book).

Unlike the earlier per-exercise image-update migrations, this one rewrites only
the ``media`` field — the previous full-document re-set would overwrite the
markdown description (set by 20260506010000) and re-introduce ``instructions``
(removed by 20260506020000).

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
    "img_1": _data_url_webp("hspu_level_1_1.webp"),
    "img_2": _data_url_webp("hspu_level_1_2.webp"),
}

_OLD_MEDIA = {
    "youtube_tutorial": "https://www.youtube.com/watch?v=4FqV_u_e2A8",
    "thumbnail_url": "https://img.youtube.com/vi/4FqV_u_e2A8/hqdefault.jpg",
}


class Migration(BaseMigration):
    def upgrade(self):
        self.db.exercises.update_one(
            {"_id": "hspu_level_1"},
            {"$set": {"media": _NEW_MEDIA}},
        )

    def downgrade(self):
        self.db.exercises.update_one(
            {"_id": "hspu_level_1"},
            {"$set": {"media": _OLD_MEDIA}},
        )
