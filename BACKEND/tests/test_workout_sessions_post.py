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
