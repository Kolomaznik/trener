from pymongo import MongoClient

from app.config import Settings, settings


def create_mongo_client(cfg: Settings | None = None) -> MongoClient:
    active = cfg or settings
    return MongoClient(active.mongo_uri)


def get_exercises_collection(cfg: Settings | None = None):
    active = cfg or settings
    client = create_mongo_client(active)
    return client[active.mongo_database][active.mongo_exercises_collection]
