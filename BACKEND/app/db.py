from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from config import settings


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)


def get_db() -> Database:
    return _client()[settings.mongo_database]
