from datetime import datetime

import pytest

from app.services.fitness_math import compute_level
from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

EXERCISE_DOC = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační a přípravný cvik.",
    "instructions": [],
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": "Pokračuj na level 2.",
    },
    "muscle_engagement_percent": {"chest": 40, "triceps": 30},
}

SESSION_PAYLOAD = {
    "exercise_id": "pushups_level_1",
    "exercise_name": "Kliky o zeď",
    "started_at": "2026-05-03T10:00:00Z",
    "ended_at": "2026-05-03T10:01:00Z",
    "total_duration_sec": 60.0,
    "total_reps": 15,
    "events": [
        {
            "value": 1,
            "token": "jedna",
            "timestamp_ms": 1000,
            "timestamp_iso": "2026-05-03T10:00:01Z",
        },
        {
            "value": 2,
            "token": "dva",
            "timestamp_ms": 2000,
            "timestamp_iso": "2026-05-03T10:00:02Z",
        },
    ],
    "set_number": 1,
}


@pytest.fixture
def seeded_db(mock_db):
    mock_db["exercises"].insert_one(EXERCISE_DOC)
    return mock_db


@pytest.fixture
def authed_client(client, fake_google):
    fake_google.set_user(google_payload(weight_kg=80.0, height_cm=180))
    client.get("/user/settings", headers=AUTH)
    fake_google.set_user(google_payload(weight_kg=80.0, height_cm=180))
    return client


# ── compute_level unit tests ─────────────────────────────────────────────────

class TestComputeLevel:
    def test_no_history_returns_beginner(self):
        assert compute_level([], None) == "beginner"

    def test_no_history_with_goals_returns_beginner(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([], goals) == "beginner"

    def test_below_beginner_threshold_returns_beginner(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([5, 6, 7], goals) == "beginner"

    def test_at_beginner_threshold_returns_intermediate(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([10, 10, 10], goals) == "intermediate"

    def test_above_beginner_below_mastery_returns_intermediate(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([20, 25, 30], goals) == "intermediate"

    def test_at_mastery_threshold_returns_mastery(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([50, 50, 50], goals) == "mastery"

    def test_above_mastery_threshold_returns_mastery(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([60, 70], goals) == "mastery"

    def test_uses_average_not_latest(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        # average = (5 + 15) / 2 = 10 → intermediate
        assert compute_level([5, 15], goals) == "intermediate"

    def test_no_goals_returns_beginner(self):
        assert compute_level([100], None) == "beginner"


# ── POST /workout-sessions ────────────────────────────────────────────────────

class TestCreateWorkoutSession:
    def test_creates_session_and_returns_201(self, authed_client, seeded_db):
        response = authed_client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)

        assert response.status_code == 201
        body = response.json()
        assert body["exercise_id"] == "pushups_level_1"
        assert body["exercise_name"] == "Kliky o zeď"
        assert body["total_reps"] == 15
        assert body["set_number"] == 1
        assert body["user_email"] == "alice@example.com"
        assert len(body["events"]) == 2

    def test_enriches_with_user_body_metrics(self, authed_client, seeded_db):
        response = authed_client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)

        body = response.json()
        assert body["user_weight_kg"] == 80.0
        assert body["user_height_cm"] == 180

    def test_enriches_with_muscle_engagement(self, authed_client, seeded_db):
        response = authed_client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)

        body = response.json()
        assert body["muscle_engagement_percent"] == {"chest": 40, "triceps": 30}

    def test_missing_user_metrics_stored_as_null(self, client, fake_google, seeded_db):
        fake_google.set_user(google_payload())
        client.get("/user/settings", headers=AUTH)
        fake_google.set_user(google_payload())

        response = client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)

        body = response.json()
        assert body["user_weight_kg"] is None
        assert body["user_height_cm"] is None

    def test_unknown_exercise_stores_empty_muscle_map(self, authed_client, seeded_db):
        payload = {**SESSION_PAYLOAD, "exercise_id": "unknown_exercise"}
        response = authed_client.post("/workout-sessions", json=payload, headers=AUTH)

        assert response.status_code == 201
        assert response.json()["muscle_engagement_percent"] == {}

    def test_requires_auth(self, client, seeded_db):
        response = client.post("/workout-sessions", json=SESSION_PAYLOAD)

        assert response.status_code in (401, 403)

    def test_validates_set_number_minimum(self, authed_client, seeded_db):
        payload = {**SESSION_PAYLOAD, "set_number": 0}
        response = authed_client.post("/workout-sessions", json=payload, headers=AUTH)

        assert response.status_code == 422

    def test_persists_to_database(self, authed_client, seeded_db):
        authed_client.post("/workout-sessions", json=SESSION_PAYLOAD, headers=AUTH)

        doc = seeded_db["workout_sessions"].find_one({"exercise_id": "pushups_level_1"})
        assert doc is not None
        assert doc["total_reps"] == 15
        assert isinstance(doc["saved_at"], datetime)


# ── GET /workout-sessions/level/{exercise_id} ─────────────────────────────────

class TestGetUserLevel:
    def _post_session(self, client, total_reps: int, set_number: int = 1):
        payload = {**SESSION_PAYLOAD, "total_reps": total_reps, "set_number": set_number}
        client.post("/workout-sessions", json=payload, headers=AUTH)

    def test_no_history_returns_beginner(self, authed_client, seeded_db):
        response = authed_client.get("/workout-sessions/level/pushups_level_1", headers=AUTH)

        assert response.status_code == 200
        body = response.json()
        assert body["level"] == "beginner"
        assert body["recent_sets"] == []
        assert body["last_best_reps"] is None
        assert body["rest_seconds"] == 90

    def test_beginner_level_includes_goals(self, authed_client, seeded_db):
        response = authed_client.get("/workout-sessions/level/pushups_level_1", headers=AUTH)

        body = response.json()
        assert body["target_reps"] == 10
        assert body["target_sets"] == 1

    def test_intermediate_level_when_avg_above_beginner(self, authed_client, seeded_db):
        self._post_session(authed_client, total_reps=20)

        response = authed_client.get("/workout-sessions/level/pushups_level_1", headers=AUTH)

        body = response.json()
        assert body["level"] == "intermediate"
        assert body["target_reps"] == 25
        assert body["target_sets"] == 2
        assert body["rest_seconds"] == 60

    def test_mastery_level_when_avg_above_mastery(self, authed_client, seeded_db):
        self._post_session(authed_client, total_reps=55)

        response = authed_client.get("/workout-sessions/level/pushups_level_1", headers=AUTH)

        body = response.json()
        assert body["level"] == "mastery"
        assert body["target_reps"] == 50
        assert body["rest_seconds"] == 45

    def test_uses_only_last_5_sessions(self, authed_client, seeded_db):
        for i in range(7):
            self._post_session(authed_client, total_reps=55, set_number=i + 1)

        response = authed_client.get("/workout-sessions/level/pushups_level_1", headers=AUTH)

        body = response.json()
        assert len(body["recent_sets"]) == 5

    def test_last_best_reps_is_max(self, authed_client, seeded_db):
        self._post_session(authed_client, total_reps=10)
        self._post_session(authed_client, total_reps=20, set_number=2)
        self._post_session(authed_client, total_reps=15, set_number=3)

        response = authed_client.get("/workout-sessions/level/pushups_level_1", headers=AUTH)

        assert response.json()["last_best_reps"] == 20

    def test_requires_auth(self, client, seeded_db):
        response = client.get("/workout-sessions/level/pushups_level_1")

        assert response.status_code in (401, 403)

    def test_unknown_exercise_returns_beginner(self, authed_client, seeded_db):
        response = authed_client.get("/workout-sessions/level/neexistuje", headers=AUTH)

        assert response.status_code == 200
        body = response.json()
        assert body["level"] == "beginner"
        assert body["target_reps"] is None
