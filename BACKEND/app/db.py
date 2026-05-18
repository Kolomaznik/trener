from functools import lru_cache
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.sql_db import fetchone
from config import settings

# Only documents carrying the full exercise schema (``level`` + ``family``)
# count as catalog exercises; legacy/partial docs are filtered out.
SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}


@lru_cache(maxsize=1)
def _client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)


def get_db() -> AsyncIOMotorDatabase:
    return _client()[settings.mongo_database]


async def get_user_weight_kg(email: str) -> float | None:
    """Read the user's weight from the Postgres ``users`` table.

    The Mongo ``users`` collection is no longer the source of truth for
    profile data -- see ``app/sql_db.py`` and ``app/api/user/get_profile.py``.
    """
    row = await fetchone("SELECT weight_kg FROM users WHERE email = %s", (email,))
    if row is None or row["weight_kg"] is None:
        return None
    return float(row["weight_kg"])
