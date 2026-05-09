"""Endpoint tests for the /user-exercises CRUD-lite resource."""

import pytest

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


@pytest.fixture
def authed_client(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)
    fake_google.set_user(google_payload())
    return client


def _seed_pushups(mock_db):
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


# ── POST /user-exercises ─────────────────────────────────────────────────────


def test_post_user_exercises_creates_row(authed_client, mock_db, fake_google):
    _seed_pushups(mock_db)
    fake_google.set_user(google_payload())

    response = authed_client.post(
        "/user-exercises",
        json={"exercise_name": "pushups_level_1"},
        headers=AUTH,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["exercise_name"] == "pushups_level_1"
    assert body["user_level"] == "beginner"
    assert body["target_reps"] == 10

    row = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert row is not None
    assert row["user_level"] == "beginner"
    assert len(row["level_history"]) == 1
    assert row["level_history"][0]["trigger"] == "seed"


def test_post_user_exercises_returns_404_for_unknown_exercise(authed_client, fake_google):
    fake_google.set_user(google_payload())
    response = authed_client.post(
        "/user-exercises",
        json={"exercise_name": "does_not_exist"},
        headers=AUTH,
    )
    assert response.status_code == 404


def test_post_user_exercises_returns_409_on_duplicate(authed_client, mock_db, fake_google):
    _seed_pushups(mock_db)

    fake_google.set_user(google_payload())
    first = authed_client.post(
        "/user-exercises",
        json={"exercise_name": "pushups_level_1"},
        headers=AUTH,
    )
    assert first.status_code == 201

    fake_google.set_user(google_payload())
    second = authed_client.post(
        "/user-exercises",
        json={"exercise_name": "pushups_level_1"},
        headers=AUTH,
    )
    assert second.status_code == 409


# ── GET /user-exercises ──────────────────────────────────────────────────────


def test_get_user_exercises_empty_for_new_user(authed_client, fake_google):
    fake_google.set_user(google_payload())
    response = authed_client.get("/user-exercises", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == []


def test_get_user_exercises_returns_added_exercises_with_catalog_data(
    authed_client,
    mock_db,
    fake_google,
):
    _seed_pushups(mock_db)
    fake_google.set_user(google_payload())
    authed_client.post(
        "/user-exercises",
        json={"exercise_name": "pushups_level_1"},
        headers=AUTH,
    )

    fake_google.set_user(google_payload())
    response = authed_client.get("/user-exercises", headers=AUTH)
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 1
    item = items[0]
    # Per-user state.
    assert item["exercise_name"] == "pushups_level_1"
    assert item["user_level"] == "beginner"
    assert item["target_reps"] == 10
    # Catalog fields joined via $lookup at read time.
    assert item["title"] == "Kliky o zeď"
    assert item["family"] == "Kliky"
    assert item["level"] == 1
