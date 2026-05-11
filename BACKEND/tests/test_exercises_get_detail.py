from datetime import UTC, datetime, timedelta

import pytest

import app.auth as auth_module
from tests.conftest import FakeAsyncClient, FakeResponse, google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

# v2 catalog row — all denormalized fields live on `exercises` only.
EXERCISE_DOC = {
    "_id": "pushups_level_1",
    "name": "pushups_level_1",
    "title": "Kliky o zeď",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační a přípravný cvik.",
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": "",
    },
    "muscle_engagement_percent": {"chest": 40},
    "level_coefficient": 0.2,
    "height_multiplier": 0.4,
}


@pytest.fixture
def seeded_db(mock_db):
    mock_db["exercises"].insert_one(EXERCISE_DOC)
    return mock_db


def _stub_google(monkeypatch):
    FakeAsyncClient.next_response = FakeResponse(200, google_payload())
    FakeAsyncClient.next_exception = None
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", FakeAsyncClient)


def test_get_exercise_detail_returns_200_anonymous(client, seeded_db):
    response = client.get("/exercises/pushups_level_1")
    assert response.status_code == 200
    assert response.json()["user_level"] is None


def test_get_exercise_detail_returns_user_level_null_when_not_added(
    client,
    mock_db,
    monkeypatch,
):
    """Authenticated user opens a detail page for an exercise they have NOT
    added. The endpoint must NOT auto-create a user_exercises row, and the
    response's user_level must be null so the frontend can render the
    'Add to my list' CTA."""
    mock_db["exercises"].insert_one(EXERCISE_DOC)
    mock_db["users"].insert_one({"email": "alice@example.com", "weight_kg": 80.0})
    _stub_google(monkeypatch)

    response = client.get("/exercises/pushups_level_1", headers=AUTH)
    assert response.status_code == 200
    body = response.json()

    # Catalog fields are present.
    assert body["title"] == "Kliky o zeď"
    # No personal state.
    assert body["user_level"] is None
    # No row was created.
    assert mock_db["user_exercises"].count_documents({}) == 0


def test_get_exercise_detail_returns_user_state_when_added(
    client,
    mock_db,
    monkeypatch,
):
    """For an exercise the user HAS added, the endpoint joins catalog data
    with the user_exercises row and refreshes its derived caches without
    advancing the streak."""
    mock_db["exercises"].insert_one(EXERCISE_DOC)
    mock_db["users"].insert_one({"email": "alice@example.com", "weight_kg": 80.0})

    now = datetime.now(UTC)
    # Pre-existing user_exercises row (matches the v2 schema: no catalog copies).
    mock_db["user_exercises"].insert_one(
        {
            "user_email": "alice@example.com",
            "exercise_name": "pushups_level_1",
            "user_level": "beginner",
            "level_history": [
                {"level": "beginner", "trigger": "seed", "achieved_at": now - timedelta(days=1)},
            ],
            "consecutive_successes": 0,
            "completed": False,
            "completed_at": None,
            "target_reps": 10,
            "target_sets": 1,
            "best_result": 0,
            "rest_seconds": 90,
            "recent_sets": [],
            "muscle_load_by_difficulty": None,
            "created_at": now - timedelta(days=1),
            "updated_at": now - timedelta(days=1),
        }
    )
    # Three series rows exercising the level_sets filter:
    # 1) at current level → included in level_sets
    # 2) at a different level → excluded
    # 3) without user_level (legacy row, pre-feature) → excluded
    mock_db["exercise_series"].insert_many(
        [
            {
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 12,
                "started_at": now,
                "set_number": 1,
                "user_level": "beginner",
            },
            {
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 30,
                "started_at": now - timedelta(days=2),
                "set_number": 1,
                "user_level": "intermediate",
            },
            {
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 8,
                "started_at": now - timedelta(days=3),
                "set_number": 1,
            },
        ]
    )
    _stub_google(monkeypatch)

    response = client.get("/exercises/pushups_level_1", headers=AUTH)
    assert response.status_code == 200
    body = response.json()

    assert body["title"] == "Kliky o zeď"
    assert body["user_level"]["level"] == "beginner"
    assert body["user_level"]["target_reps"] == 10
    # last_best_reps is intentionally cross-level (best across all series).
    assert body["user_level"]["last_best_reps"] == 30

    # level_sets contains only the current-level row; intermediate and
    # legacy (no user_level) rows are filtered out.
    level_sets = body["user_level"]["level_sets"]
    assert len(level_sets) == 1
    assert level_sets[0]["total_reps"] == 12
    assert level_sets[0]["set_number"] == 1

    # Read-only: the endpoint did NOT advance the streak.
    row = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert row["user_level"] == "beginner"
    assert row["consecutive_successes"] == 0
