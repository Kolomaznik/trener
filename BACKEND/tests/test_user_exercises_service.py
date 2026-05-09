import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.services.user_exercises import (
    UserExerciseAlreadyExists,
    add_user_exercise,
    list_user_exercises,
    refresh_user_exercise,
)

USER = "alice@example.com"
PUSHUPS = "pushups_level_1"


def _seed_exercises(mock_db):
    mock_db["exercises"].insert_many(
        [
            {
                "_id": "pushups_level_1",
                "name": "pushups_level_1",
                "title": "Kliky o zeď",
                "family": "Kliky",
                "level": 1,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 50},
                },
                "muscle_engagement_percent": {"chest": 40},
                "level_coefficient": 0.2,
                "height_multiplier": 0.4,
            },
            {
                "_id": "pushups_level_2",
                "name": "pushups_level_2",
                "title": "Kliky v předklonu",
                "family": "Kliky",
                "level": 2,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 20},
                    "mastery": {"sets": 3, "reps": 40},
                },
                "muscle_engagement_percent": {"chest": 40},
                "level_coefficient": 0.35,
                "height_multiplier": 0.4,
            },
            {
                "_id": "squats_level_1",
                "name": "squats_level_1",
                "title": "Dřepy ve svíčce",
                "family": "Dřepy",
                "level": 1,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 50},
                },
                "muscle_engagement_percent": {"quadriceps": 40},
                "level_coefficient": 0.25,
                "height_multiplier": 0.5,
            },
        ]
    )


def _async_db(mock_db):
    return AsyncMongoMockClient(mock_mongo_client=mock_db.client)["test_db"]


def _add_pushups(async_db):
    """Explicitly add pushups_level_1 for the test user (replaces auto-seed)."""
    return asyncio.run(
        add_user_exercise(
            db=async_db,
            user_email=USER,
            exercise_name=PUSHUPS,
        )
    )


def _run_set(async_db, mock_db, *, total_reps, set_number, started_at):
    """Insert a exercise_series row and call refresh_user_exercise once.

    The user must have already added the exercise via add_user_exercise —
    refresh_user_exercise no longer auto-creates rows.
    """
    mock_db["exercise_series"].insert_one(
        {
            "user_email": USER,
            "exercise_id": PUSHUPS,
            "total_reps": total_reps,
            "started_at": started_at,
            "set_number": set_number,
        }
    )
    return asyncio.run(
        refresh_user_exercise(
            db=async_db,
            user_email=USER,
            exercise_name=PUSHUPS,
        )
    )


# ── add_user_exercise ────────────────────────────────────────────────────────


def test_add_user_exercise_creates_row_at_beginner_level(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)

    doc = _add_pushups(async_db)

    assert doc["user_email"] == USER
    assert doc["exercise_name"] == PUSHUPS
    assert doc["user_level"] == "beginner"
    assert doc["completed"] is False
    assert len(doc["level_history"]) == 1
    assert doc["level_history"][0]["level"] == "beginner"
    assert doc["level_history"][0]["trigger"] == "seed"
    # consecutive_successes is set lazily on the first successful set —
    # it must NOT be present on the freshly inserted row.
    assert "consecutive_successes" not in doc

    # The DB row is slim: only the six intrinsic fields. No catalog
    # copies AND no derived caches (target_*, best_result, recent_sets,
    # muscle_load_by_difficulty, rest_seconds, updated_at, completed_at).
    forbidden_fields = {
        "title",
        "family",
        "level",
        "description",
        "media",
        "cadence",
        "progression_goals",
        "muscle_engagement_percent",
        "level_coefficient",
        "height_multiplier",
        "target_reps",
        "target_sets",
        "rest_seconds",
        "best_result",
        "recent_sets",
        "muscle_load_by_difficulty",
        "updated_at",
        "completed_at",
        "consecutive_successes",
    }
    raw = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    leaked = forbidden_fields & set(raw.keys())
    assert not leaked, f"slim user_exercises row leaked fields: {leaked}"
    # Six intrinsic keys plus the auto-generated _id.
    assert set(raw.keys()) == {
        "_id",
        "user_email",
        "exercise_name",
        "user_level",
        "completed",
        "level_history",
        "created_at",
    }


def test_add_user_exercise_raises_on_duplicate(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)

    with pytest.raises(UserExerciseAlreadyExists):
        _add_pushups(async_db)


def test_add_user_exercise_raises_on_unknown_exercise(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)

    with pytest.raises(ValueError):
        asyncio.run(
            add_user_exercise(
                db=async_db,
                user_email=USER,
                exercise_name="does_not_exist",
            )
        )


# ── list_user_exercises ──────────────────────────────────────────────────────


def test_list_user_exercises_empty_when_nothing_added(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)

    docs = asyncio.run(list_user_exercises(db=async_db, user_email=USER))
    assert docs == []


def test_list_user_exercises_joins_catalog_and_derives_targets(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)

    docs = asyncio.run(list_user_exercises(db=async_db, user_email=USER))
    assert len(docs) == 1
    doc = docs[0]
    # Catalog title/family/level joined via $lookup at read time.
    assert doc["title"] == "Kliky o zeď"
    assert doc["family"] == "Kliky"
    assert doc["level"] == 1
    # Per-user state.
    assert doc["user_level"] == "beginner"
    # Derived from catalog progression_goals[user_level], not cached.
    assert doc["target_reps"] == 10
    assert doc["target_sets"] == 1
    # Derived from REST_SECONDS[user_level], not cached.
    assert doc["rest_seconds"] == 90  # beginner rest
    # The list endpoint deliberately does NOT include per-set history.
    assert "best_result" not in doc
    assert "recent_sets" not in doc


# ── refresh_user_exercise without an existing row ────────────────────────────


def test_refresh_user_exercise_returns_none_when_not_added(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    mock_db["exercise_series"].insert_one(
        {
            "user_email": USER,
            "exercise_id": PUSHUPS,
            "total_reps": 12,
            "started_at": datetime.now(UTC),
            "set_number": 1,
        }
    )

    level_up = asyncio.run(
        refresh_user_exercise(
            db=async_db,
            user_email=USER,
            exercise_name=PUSHUPS,
        )
    )
    assert level_up is None
    # Submitting a session for an unadded exercise must NOT create a row.
    assert mock_db["user_exercises"].count_documents({}) == 0


# ── Streak machine (requires explicit add first) ─────────────────────────────


def test_refresh_advances_streak_only_on_latest_session(mock_db):
    """Latest above-target session ticks the streak; older sessions don't.

    Best result and recent_sets used to be cached on the row but are now
    derived at read time by the detail endpoint — they must NOT appear
    on the slim user_exercises doc.
    """
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)

    now = datetime.now(UTC)
    mock_db["exercise_series"].insert_many(
        [
            {
                "user_email": USER,
                "exercise_id": PUSHUPS,
                "total_reps": 8,
                "started_at": now - timedelta(days=3),
                "set_number": 1,
            },
            {
                "user_email": USER,
                "exercise_id": PUSHUPS,
                "total_reps": 9,
                "started_at": now - timedelta(days=2),
                "set_number": 2,
            },
            {
                "user_email": USER,
                "exercise_id": PUSHUPS,
                "total_reps": 14,
                "started_at": now - timedelta(days=1),
                "set_number": 3,
            },
        ]
    )

    asyncio.run(refresh_user_exercise(db=async_db, user_email=USER, exercise_name=PUSHUPS))

    doc = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    # Latest set (14 reps) is above target=10 → streak = 1, but no level-up
    # yet (threshold = 3).
    assert doc["user_level"] == "beginner"
    assert doc["consecutive_successes"] == 1
    # Caches are gone.
    assert "best_result" not in doc
    assert "recent_sets" not in doc


def test_no_advance_on_insufficient_reps(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)
    now = datetime.now(UTC)
    mock_db["exercise_series"].insert_many(
        [
            {
                "user_email": USER,
                "exercise_id": PUSHUPS,
                "total_reps": 8,
                "started_at": now - timedelta(days=2),
                "set_number": 1,
            },
            {
                "user_email": USER,
                "exercise_id": PUSHUPS,
                "total_reps": 9,
                "started_at": now - timedelta(days=1),
                "set_number": 2,
            },
        ]
    )

    level_up = asyncio.run(
        refresh_user_exercise(db=async_db, user_email=USER, exercise_name=PUSHUPS)
    )

    doc = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    assert level_up is None
    assert doc["user_level"] == "beginner"
    # No successful set ever happened, so the streak counter was never
    # written — the field stays absent rather than being set to 0.
    assert "consecutive_successes" not in doc


def test_advance_beginner_to_intermediate_after_three_successes(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)
    now = datetime.now(UTC)

    # First two successes — streak grows but no level-up yet.
    for offset in (1, 2):
        level_up = _run_set(
            async_db,
            mock_db,
            total_reps=10,
            set_number=offset,
            started_at=now + timedelta(minutes=offset),
        )
        assert level_up is None

    doc_before = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    assert doc_before["user_level"] == "beginner"
    assert doc_before["consecutive_successes"] == 2

    # Third success — streak hits LEVEL_UP_THRESHOLD = 3 → advance.
    level_up = _run_set(
        async_db,
        mock_db,
        total_reps=10,
        set_number=3,
        started_at=now + timedelta(minutes=3),
    )

    doc = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    achievement = mock_db["user_achievements"].find_one({"user_email": USER})
    assert level_up is not None
    assert level_up.previous_level == "beginner"
    assert level_up.new_level == "intermediate"
    assert doc["user_level"] == "intermediate"
    assert doc["consecutive_successes"] == 0
    # target_reps is no longer cached on the row — the post-level-up
    # snapshot has only the streak/level fields.
    assert "target_reps" not in doc
    history = doc["level_history"]
    assert [entry["level"] for entry in history] == ["beginner", "intermediate"]
    assert history[1]["trigger"] == "consecutive_successes"
    assert achievement["cells"]["pushups"]["1"]["stars"] == 1


def test_mastery_completion_does_not_auto_unlock_next_exercise(mock_db):
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)
    now = datetime.now(UTC)

    # 9 sets total: 3 × 10 (→ intermediate), 3 × 25 (→ mastery), 3 × 50 (→ completed).
    timeline = [10, 10, 10, 25, 25, 25, 50, 50, 50]
    level_up = None
    for offset, reps in enumerate(timeline, start=1):
        level_up = _run_set(
            async_db,
            mock_db,
            total_reps=reps,
            set_number=offset,
            started_at=now + timedelta(minutes=offset),
        )

    completed_doc = mock_db["user_exercises"].find_one(
        {"user_email": USER, "exercise_name": PUSHUPS}
    )
    next_doc = mock_db["user_exercises"].find_one(
        {"user_email": USER, "exercise_name": "pushups_level_2"}
    )
    achievement = mock_db["user_achievements"].find_one({"user_email": USER})
    assert level_up is not None
    assert level_up.previous_level == "mastery"
    assert level_up.new_level == "completed"
    assert completed_doc["completed"] is True
    # completed_at is no longer mirrored on the row; the timestamp lives
    # on the last level_history entry.
    assert "completed_at" not in completed_doc
    completed_entry = completed_doc["level_history"][-1]
    assert completed_entry["level"] == "completed"
    assert completed_entry["achieved_at"] is not None
    # The next exercise in the family is NOT auto-added — that's the user's
    # explicit call now.
    assert next_doc is None
    assert [e["level"] for e in completed_doc["level_history"]] == [
        "beginner",
        "intermediate",
        "mastery",
        "completed",
    ]
    assert achievement["cells"]["pushups"]["1"]["stars"] == 3


def test_failure_resets_streak(mock_db):
    """One under-target set zeroes the streak; subsequent successes count from zero."""
    _seed_exercises(mock_db)
    async_db = _async_db(mock_db)
    _add_pushups(async_db)
    now = datetime.now(UTC)

    # Two successes — streak = 2.
    for offset in (1, 2):
        _run_set(
            async_db,
            mock_db,
            total_reps=10,
            set_number=offset,
            started_at=now + timedelta(minutes=offset),
        )
    doc = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    assert doc["consecutive_successes"] == 2

    # One failure — streak resets.
    level_up = _run_set(
        async_db,
        mock_db,
        total_reps=8,
        set_number=3,
        started_at=now + timedelta(minutes=3),
    )
    assert level_up is None
    doc = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    assert doc["user_level"] == "beginner"
    assert doc["consecutive_successes"] == 0

    # Three more successes after the reset → level-up.
    for offset in (4, 5, 6):
        level_up = _run_set(
            async_db,
            mock_db,
            total_reps=10,
            set_number=offset,
            started_at=now + timedelta(minutes=offset),
        )

    doc = mock_db["user_exercises"].find_one({"user_email": USER, "exercise_name": PUSHUPS})
    assert level_up is not None
    assert level_up.new_level == "intermediate"
    assert doc["user_level"] == "intermediate"
    assert doc["consecutive_successes"] == 0
