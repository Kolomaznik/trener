from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import settings


@lru_cache(maxsize=1)
def _client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)


def get_db() -> AsyncIOMotorDatabase:
    return _client()[settings.mongo_database]
