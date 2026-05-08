import pytest

import app.api.exercises.get_detail as get_detail_module
from tests.conftest import FakeAsyncClient, FakeResponse, google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

EXERCISE_DOC = {
    "_id": "pushups_level_1",
    "name": "pushups_level_1",
    "title": "Kliky o zeď",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační a přípravný cvik.",
}


@pytest.fixture
def seeded_db(mock_db):
    mock_db["exercises"].insert_one(EXERCISE_DOC)
    return mock_db


def test_get_exercise_detail_returns_200(client, seeded_db):
    response = client.get("/exercises/pushups_level_1")
    assert response.status_code == 200


def test_get_exercise_detail_reads_from_user_exercises_for_authenticated_user(
    client,
    mock_db,
    monkeypatch,
):
    mock_db["user_exercises"].insert_one(
        {
            "user_email": "alice@example.com",
            "exercise_name": "pushups_level_1",
            "title": "Kliky o zeď",
            "family": "Kliky",
            "level": 1,
            "description": "Rehabilitační a přípravný cvik.",
            "media": {},
            "cadence": None,
            "progression_goals": {
                "beginner": {"sets": 1, "reps": 10},
                "intermediate": {"sets": 2, "reps": 25},
                "mastery": {"sets": 3, "reps": 50},
                "coach_note": "",
            },
            "muscle_engagement_percent": {"chest": 40},
            "level_coefficient": 0.2,
            "height_multiplier": 0.4,
            "next_exercise_name": "pushups_level_2",
            "next_exercise_title": "Kliky v předklonu",
            "user_level": "beginner",
            "target_reps": 10,
            "target_sets": 1,
            "best_result": 12,
            "rest_seconds": 90,
            "recent_sets": [],
            "muscle_load_by_difficulty": {"beginner": {}, "intermediate": {}, "mastery": {}},
        }
    )
    mock_db["users"].insert_one({"email": "alice@example.com", "weight_kg": 80.0})

    FakeAsyncClient.next_response = FakeResponse(200, google_payload())
    FakeAsyncClient.next_exception = None
    monkeypatch.setattr(get_detail_module.httpx, "AsyncClient", FakeAsyncClient)

    response = client.get("/exercises/pushups_level_1", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "pushups_level_1"
    assert body["user_level"]["level"] == "beginner"
    assert body["user_level"]["last_best_reps"] == 12
