import asyncio
from datetime import UTC, datetime, timedelta

from mongomock_motor import AsyncMongoMockClient

from app.services.user_exercises import get_or_seed_user_exercises, refresh_user_exercise


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
            {
                "_id": "pullups_level_1",
                "name": "pullups_level_1",
                "title": "Svislé přítahy",
                "family": "Shyby",
                "level": 1,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 20},
                    "mastery": {"sets": 3, "reps": 40},
                },
                "muscle_engagement_percent": {"lats": 30},
                "level_coefficient": 0.3,
                "height_multiplier": 0.55,
            },
            {
                "_id": "legraises_level_1",
                "name": "legraises_level_1",
                "title": "Přítahy kolen v sedě",
                "family": "Zdvihy nohou",
                "level": 1,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 40},
                },
                "muscle_engagement_percent": {"abs": 45},
                "level_coefficient": 0.2,
                "height_multiplier": 0.3,
            },
            {
                "_id": "bridges_level_1",
                "name": "bridges_level_1",
                "title": "Krátké mosty",
                "family": "Mosty",
                "level": 1,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 50},
                },
                "muscle_engagement_percent": {"glutes": 40},
                "level_coefficient": 0.3,
                "height_multiplier": 0.25,
            },
            {
                "_id": "hspu_level_1",
                "name": "hspu_level_1",
                "title": "Stojka na hlavě o zeď",
                "family": "Kliky ve stojce",
                "level": 1,
                "description": "x",
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 30},
                    "intermediate": {"sets": 1, "reps": 60},
                    "mastery": {"sets": 1, "reps": 120},
                },
                "muscle_engagement_percent": {"deltoids": 30},
                "level_coefficient": 0.5,
                "height_multiplier": 0.45,
            },
        ]
    )


def test_get_or_seed_user_exercises_creates_big5_docs(mock_db):
    _seed_exercises(mock_db)
    async_db = AsyncMongoMockClient(mock_mongo_client=mock_db.client)["test_db"]

    docs = asyncio.run(
        get_or_seed_user_exercises(
            db=async_db,
            user_email="alice@example.com",
            weight_kg=80.0,
        )
    )

    assert len(docs) == 5
    assert {doc["exercise_name"] for doc in docs} == {
        "pushups_level_1",
        "squats_level_1",
        "pullups_level_1",
        "legraises_level_1",
        "bridges_level_1",
    }
    assert all(doc["user_level"] == "beginner" for doc in docs)


def test_refresh_user_exercise_updates_progress_and_best_result(mock_db):
    _seed_exercises(mock_db)
    now = datetime.now(UTC)
    mock_db["workout_sessions"].insert_many(
        [
            {
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 8,
                "started_at": now - timedelta(days=3),
                "set_number": 1,
            },
            {
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 12,
                "started_at": now - timedelta(days=2),
                "set_number": 2,
            },
            {
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 14,
                "started_at": now - timedelta(days=1),
                "set_number": 3,
            },
        ]
    )
    async_db = AsyncMongoMockClient(mock_mongo_client=mock_db.client)["test_db"]

    asyncio.run(
        refresh_user_exercise(
            db=async_db,
            user_email="alice@example.com",
            exercise_name="pushups_level_1",
            weight_kg=80.0,
        )
    )

    doc = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert doc is not None
    assert doc["best_result"] == 14
    assert doc["user_level"] == "intermediate"
    assert doc["target_reps"] == 25
    assert len(doc["recent_sets"]) == 3
