import pytest

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

SESSION_PAYLOAD = {
    "exercise_id": "pushups_level_1",
    "exercise_name": "Kliky o zeď",
    "started_at": "2026-05-03T10:00:00Z",
    "ended_at": "2026-05-03T10:01:00Z",
    "total_duration_sec": 60.0,
    "total_reps": 15,
    "events": [],
    "set_number": 1,
}


@pytest.fixture
def authed_client(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)
    fake_google.set_user(google_payload())
    return client


def test_post_workout_session_returns_201(authed_client):
    response = authed_client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)
    assert response.status_code == 201


def test_post_workout_session_refreshes_user_exercises(authed_client, mock_db):
    mock_db["exercises"].insert_one(
        {
            "_id": "pushups_level_1",
            "name": "pushups_level_1",
            "title": "Kliky o zeď",
            "family": "Kliky",
            "level": 1,
            "progression_goals": {
                "beginner": {"sets": 1, "reps": 10},
                "intermediate": {"sets": 2, "reps": 25},
                "mastery": {"sets": 3, "reps": 50},
            },
            "muscle_engagement_percent": {"chest": 40},
            "level_coefficient": 0.2,
            "height_multiplier": 0.4,
        }
    )

    response = authed_client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)
    assert response.status_code == 201

    user_exercise = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert user_exercise is not None
    assert user_exercise["best_result"] == 0
    assert user_exercise["user_level"] == "beginner"
    assert len(user_exercise["recent_sets"]) == 1
