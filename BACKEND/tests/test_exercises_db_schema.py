"""Validate every document in the `exercises` collection against the
canonical Pydantic schema from this BACKEND project.

The test:
1. Discovers every migration file in the sibling ``MONGO_DB/migrations``
   directory, sorts by timestamp prefix.
2. Applies each migration's ``upgrade()`` against a fresh mongomock
   database (same order as ``mongodb_migrations.MigrationManager``).
3. Iterates every document in ``db.exercises`` and validates it with
   ``ExerciseDocument`` from ``app.schemas.exercises``.

Failures are aggregated and reported together so you see *all* offending
documents in a single run rather than only the first.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import mongomock
import pytest
from pydantic import ValidationError

from app.schemas.exercises import ExerciseDocument

# tests/__file__ → BACKEND/ → repo root → MONGO_DB/migrations
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "MONGO_DB" / "migrations"


def _discover_migration_modules() -> list[tuple[str, type]]:
    """Return [(timestamp_prefix, Migration class), ...] sorted by filename.

    ``mongodb_migrations`` runs migrations in alphabetical order of filename,
    which is chronological because every name starts with a timestamp.
    """
    found: list[tuple[str, type]] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9]*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migration_cls = getattr(module, "Migration", None)
        if migration_cls is not None:
            found.append((path.stem, migration_cls))
    return found


def _apply_all_migrations(db) -> None:
    """Instantiate each Migration class and run ``upgrade()`` against ``db``.

    ``BaseMigration.__init__`` connects to a real MongoDB; bypass it via
    ``__new__`` and inject our mongomock database directly (same trick used in
    ``test_users_email_unique_index.py``).
    """
    for _, migration_cls in _discover_migration_modules():
        instance = migration_cls.__new__(migration_cls)
        instance.db = db
        instance.upgrade()


@pytest.fixture
def seeded_db():
    db = mongomock.MongoClient()["test_db"]
    _apply_all_migrations(db)
    return db


def test_migrations_seed_at_least_one_exercise(seeded_db):
    """Sanity check: the seed migrations actually populate the collection."""
    count = seeded_db["exercises"].count_documents({})
    assert count > 0, "exercises collection is empty after applying all migrations"


def test_every_exercise_document_matches_schema(seeded_db):
    """Each document in `db.exercises` must validate against
    ``app.schemas.exercises.ExerciseDocument``."""
    docs = list(seeded_db["exercises"].find({}))
    failures: list[str] = []

    for doc in docs:
        doc_id = doc.get("_id") or doc.get("id") or "<unknown>"
        try:
            ExerciseDocument.model_validate(doc)
        except ValidationError as error:
            issues = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in error.errors()
            )
            failures.append(f"{doc_id} -> {issues}")

    if failures:
        msg = "\n".join(["Documents that fail ExerciseDocument validation:", *failures])
        pytest.fail(msg)


def test_seed_migration_round_trips_through_schema(seeded_db):
    """Round-trip check: validated documents serialize back to the same
    user-visible payload (no field is silently dropped or coerced)."""
    docs = list(seeded_db["exercises"].find({}))
    for doc in docs:
        try:
            model = ExerciseDocument.model_validate(doc)
        except ValidationError:
            continue  # surfaced by the previous test
        dumped = model.model_dump()
        for field in ExerciseDocument.model_fields:
            if field in doc:
                assert (
                    dumped[field] == doc[field]
                ), f"{doc.get('_id')}: field {field!r} mutated during validation"
