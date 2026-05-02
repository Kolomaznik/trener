import mongomock
import pytest
from pymongo.errors import DuplicateKeyError

from migrate import run


def test_migrate_creates_unique_email_index():
    db = mongomock.MongoClient()["test_db"]
    indexes = run(db)
    names = {idx["name"] for idx in indexes}
    assert "users_email_unique" in names

    target = next(idx for idx in indexes if idx["name"] == "users_email_unique")
    assert dict(target["key"]) == {"email": 1}
    assert target.get("unique") is True


def test_migrate_is_idempotent():
    db = mongomock.MongoClient()["test_db"]
    run(db)
    run(db)
    run(db)
    indexes = list(db["users"].list_indexes())
    matching = [idx for idx in indexes if idx["name"] == "users_email_unique"]
    assert len(matching) == 1


def test_unique_email_index_prevents_duplicate_inserts():
    db = mongomock.MongoClient()["test_db"]
    run(db)
    db["users"].insert_one({"email": "a@b.cz", "name": "first"})
    with pytest.raises(DuplicateKeyError):
        db["users"].insert_one({"email": "a@b.cz", "name": "second"})
