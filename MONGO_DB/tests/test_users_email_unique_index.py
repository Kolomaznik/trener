import importlib.util
from pathlib import Path

import mongomock
import pytest
from pymongo.errors import DuplicateKeyError

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "20260502070000_schema_ensure_users_email_unique_index.py"
)


def _load_migration_class():
    """mongodb-migrations filenames are not valid python identifiers, so we
    import via importlib instead of a regular `import`."""
    spec = importlib.util.spec_from_file_location("ensure_email_index", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Migration


def _build_migration(db) -> object:
    """BaseMigration.__init__ requires a real Mongo URL; bypass it and inject db."""
    Migration = _load_migration_class()
    instance = Migration.__new__(Migration)
    instance.db = db
    return instance


@pytest.fixture
def db():
    return mongomock.MongoClient()["test_db"]


def test_upgrade_creates_unique_email_index(db):
    migration = _build_migration(db)
    migration.upgrade()

    indexes = list(db["users"].list_indexes())
    target = next((idx for idx in indexes if idx["name"] == "users_email_unique"), None)
    assert target is not None, "users_email_unique index was not created"
    assert dict(target["key"]) == {"email": 1}
    assert target.get("unique") is True


def test_upgrade_is_idempotent(db):
    migration = _build_migration(db)
    migration.upgrade()
    migration.upgrade()
    migration.upgrade()

    matching = [idx for idx in db["users"].list_indexes() if idx["name"] == "users_email_unique"]
    assert len(matching) == 1


def test_unique_index_blocks_duplicate_emails(db):
    migration = _build_migration(db)
    migration.upgrade()

    db["users"].insert_one({"email": "a@b.cz", "name": "first"})
    with pytest.raises(DuplicateKeyError):
        db["users"].insert_one({"email": "a@b.cz", "name": "second"})


def test_downgrade_drops_the_index(db):
    migration = _build_migration(db)
    migration.upgrade()
    assert any(idx["name"] == "users_email_unique" for idx in db["users"].list_indexes())

    migration.downgrade()
    assert not any(idx["name"] == "users_email_unique" for idx in db["users"].list_indexes())


def test_downgrade_is_safe_when_index_missing(db):
    migration = _build_migration(db)
    migration.downgrade()


def test_upgrade_is_noop_when_default_named_email_index_already_exists(db):
    """Regression test: migration #1 in production created the index with
    pymongo's default name `email_1`. Re-applying this migration must NOT
    raise IndexOptionsConflict — it should detect the existing unique
    index and skip creation."""
    db["users"].create_index("email", unique=True)
    indexes_before = list(db["users"].list_indexes())

    migration = _build_migration(db)
    migration.upgrade()

    indexes_after = list(db["users"].list_indexes())
    assert len(indexes_after) == len(indexes_before)
    assert any(idx["name"] == "email_1" for idx in indexes_after)
    assert not any(idx["name"] == "users_email_unique" for idx in indexes_after)
