from functools import lru_cache
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

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


async def get_user_weight_kg(db: AsyncIOMotorDatabase, email: str) -> float | None:
    user_doc = await db["users"].find_one({"email": email})
    if user_doc is None:
        return None
    raw = user_doc.get("weight_kg")
    return float(raw) if raw is not None else None
