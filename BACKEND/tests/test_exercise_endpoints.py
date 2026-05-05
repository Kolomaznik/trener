"""Tests for exercise endpoints: family listing and embedded muscle-load in detail."""

from datetime import UTC, datetime

import pytest

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

PUSHUPS_LEVEL_1 = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační a přípravný cvik.",
    "instructions": ["Postav se čelem ke zdi."],
    "muscle_engagement_percent": {
        "chest": 40,
        "triceps": 30,
        "deltoids": 15,
        "abs": 5,
        "lower_back": 5,
        "hands": 5,
    },
    "level_coefficient": 0.20,
    "height_multiplier": 0.40,
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": "Po zvládnutí mastery na level 2.",
    },
}

PUSHUPS_LEVEL_2 = {
    "_id": "pushups_level_2",
    "id": "pushups_level_2",
    "name": "Kliky v předklonu",
    "family": "Kliky",
    "level": 2,
    "description": "Mírně náročnější varianta.",
    "instructions": ["Opři se o lavici."],
    "muscle_engagement_percent": {"chest": 50, "triceps": 30, "deltoids": 15, "abs": 5},
    "level_coefficient": 0.35,
    "height_multiplier": 0.40,
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 20},
        "mastery": {"sets": 3, "reps": 40},
        "coach_note": "Po zvládnutí pokračuj na level 3.",
    },
}

SQUATS_LEVEL_1 = {
    "_id": "squats_level_1",
    "id": "squats_level_1",
    "name": "Dřep o židli",
    "family": "Dřepy",
    "level": 1,
    "description": "Základní rehabilitační dřep.",
    "instructions": ["Posaď se a postav."],
    "muscle_engagement_percent": {},
    "level_coefficient": 0.25,
    "height_multiplier": 0.50,
}


@pytest.fixture
def seeded_db(mock_db):
    mock_db["exercises"].insert_many([PUSHUPS_LEVEL_1, PUSHUPS_LEVEL_2, SQUATS_LEVEL_1])
    return mock_db


def _seed_user(mock_db, weight_kg: float | None = 80.0) -> None:
    """Insert a user profile directly into mock_db without going through the API."""
    mock_db["users"].insert_one(
        {
            "email": "alice@example.com",
            "weight_kg": weight_kg,
            "created_at": datetime.now(UTC),
        }
    )


# ── /exercises/family/{family} ────────────────────────────────────────────────


def test_family_returns_exercises_sorted_by_level(client, seeded_db):
    response = client.get("/exercises/family/Kliky")

    assert response.status_code == 200
    body = response.json()
    levels = [item["level"] for item in body]
    assert levels == sorted(levels)
    assert all(item["family"] == "Kliky" for item in body)


def test_family_returns_correct_exercises(client, seeded_db):
    response = client.get("/exercises/family/Kliky")

    ids = [item["id"] for item in response.json()]
    assert "pushups_level_1" in ids
    assert "pushups_level_2" in ids
    assert "squats_level_1" not in ids


def test_family_404_when_unknown(client, seeded_db):
    response = client.get("/exercises/family/Neexistuje")

    assert response.status_code == 404


def test_family_includes_coefficients(client, seeded_db):
    response = client.get("/exercises/family/Kliky")

    item = response.json()[0]
    assert "level_coefficient" in item
    assert "height_multiplier" in item
    assert item["level_coefficient"] == pytest.approx(0.20)
    assert item["height_multiplier"] == pytest.approx(0.40)


# ── GET /exercises/{id} — unauthenticated ─────────────────────────────────────


def test_detail_returns_exercise(client, seeded_db):
    response = client.get("/exercises/pushups_level_1")

    assert response.status_code == 200
    assert response.json()["id"] == "pushups_level_1"


def test_detail_has_null_muscle_load_when_unauthenticated(client, seeded_db):
    response = client.get("/exercises/pushups_level_1")

    assert response.status_code == 200
    assert response.json()["muscle_load_by_difficulty"] is None


def test_detail_404_for_unknown_exercise(client, seeded_db):
    response = client.get("/exercises/neexistuje")

    assert response.status_code == 404


# ── GET /exercises/{id} — authenticated, weight set ──────────────────────────


def test_detail_includes_muscle_load_when_authenticated(client, seeded_db, fake_google, mock_db):
    """Verify that muscle_load_by_difficulty is populated and uses the kg formula."""
    _seed_user(mock_db, weight_kg=80.0)
    fake_google.set_user(google_payload())

    response = client.get("/exercises/pushups_level_1", headers=AUTH)

    assert response.status_code == 200
    mld = response.json()["muscle_load_by_difficulty"]
    assert mld is not None

    # beginner: 1×10 = 10 reps → 80 * 10 * 0.20 = 160 kg total; chest 40% = 64 kg
    assert mld["beginner"]["chest"]["muscle_load"] == pytest.approx(64.0)
    # intermediate: 2×25 = 50 reps → 80 * 50 * 0.20 = 800 kg total; chest 40% = 320 kg
    assert mld["intermediate"]["chest"]["muscle_load"] == pytest.approx(320.0)
    # mastery: 3×50 = 150 reps → 80 * 150 * 0.20 = 2400 kg total; chest 40% = 960 kg
    assert mld["mastery"]["chest"]["muscle_load"] == pytest.approx(960.0)


def test_detail_muscle_load_preserves_percent(client, seeded_db, fake_google, mock_db):
    _seed_user(mock_db, weight_kg=80.0)
    fake_google.set_user(google_payload())

    response = client.get("/exercises/pushups_level_1", headers=AUTH)

    mld = response.json()["muscle_load_by_difficulty"]
    assert mld["beginner"]["chest"]["percent"] == 40
    assert mld["beginner"]["triceps"]["percent"] == 30


def test_detail_has_null_muscle_load_when_weight_not_set(client, seeded_db, fake_google, mock_db):
    """Weight_kg=None in user profile → muscle_load_by_difficulty must be null."""
    _seed_user(mock_db, weight_kg=None)
    fake_google.set_user(google_payload())

    response = client.get("/exercises/pushups_level_1", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["muscle_load_by_difficulty"] is None


def test_detail_scales_with_user_weight(client, seeded_db, fake_google, mock_db):
    """A user twice as heavy should produce exactly twice the muscle load."""
    _seed_user(mock_db, weight_kg=80.0)
    fake_google.set_user(google_payload())
    body_80 = client.get("/exercises/pushups_level_1", headers=AUTH).json()

    mock_db["users"].update_one({"email": "alice@example.com"}, {"$set": {"weight_kg": 160.0}})
    fake_google.set_user(google_payload())
    body_160 = client.get("/exercises/pushups_level_1", headers=AUTH).json()

    load_80 = body_80["muscle_load_by_difficulty"]["beginner"]["chest"]["muscle_load"]
    load_160 = body_160["muscle_load_by_difficulty"]["beginner"]["chest"]["muscle_load"]
    assert load_160 == pytest.approx(2 * load_80)


# ── GET /exercises/{id} — user_level embedding ────────────────────────────────


class TestExerciseDetailUserLevel:
    def test_user_level_is_null_when_unauthenticated(self, client, seeded_db):
        response = client.get("/exercises/pushups_level_1")

        assert response.status_code == 200
        assert response.json()["user_level"] is None

    def test_user_level_is_beginner_with_no_history(self, client, seeded_db, fake_google):
        fake_google.set_user(google_payload())

        response = client.get("/exercises/pushups_level_1", headers=AUTH)

        assert response.status_code == 200
        user_level = response.json()["user_level"]
        assert user_level is not None
        assert user_level["level"] == "beginner"
        assert user_level["recent_sets"] == []
        assert user_level["last_best_reps"] is None
        assert user_level["rest_seconds"] == 90

    def test_user_level_includes_goals_when_no_history(self, client, seeded_db, fake_google):
        fake_google.set_user(google_payload())

        response = client.get("/exercises/pushups_level_1", headers=AUTH)

        user_level = response.json()["user_level"]
        assert user_level["target_reps"] == 10
        assert user_level["target_sets"] == 1

    def test_user_level_updates_with_session_history(self, client, seeded_db, fake_google, mock_db):
        mock_db["workout_sessions"].insert_one({
            "user_email": "alice@example.com",
            "exercise_id": "pushups_level_1",
            "total_reps": 20,
            "started_at": "2026-05-03T10:00:00Z",
            "set_number": 1,
        })
        fake_google.set_user(google_payload())

        response = client.get("/exercises/pushups_level_1", headers=AUTH)

        user_level = response.json()["user_level"]
        assert user_level["level"] == "intermediate"
        assert user_level["last_best_reps"] == 20
        assert user_level["rest_seconds"] == 60

    def test_user_level_reflects_mastery_when_high_avg(self, client, seeded_db, fake_google, mock_db):
        mock_db["workout_sessions"].insert_one({
            "user_email": "alice@example.com",
            "exercise_id": "pushups_level_1",
            "total_reps": 55,
            "started_at": "2026-05-03T10:00:00Z",
            "set_number": 1,
        })
        fake_google.set_user(google_payload())

        response = client.get("/exercises/pushups_level_1", headers=AUTH)

        user_level = response.json()["user_level"]
        assert user_level["level"] == "mastery"
        assert user_level["rest_seconds"] == 45

    def test_user_level_uses_last_5_sessions_only(self, client, seeded_db, fake_google, mock_db):
        for i in range(7):
            mock_db["workout_sessions"].insert_one({
                "user_email": "alice@example.com",
                "exercise_id": "pushups_level_1",
                "total_reps": 55,
                "started_at": f"2026-05-0{i + 1}T10:00:00Z",
                "set_number": i + 1,
            })
        fake_google.set_user(google_payload())

        response = client.get("/exercises/pushups_level_1", headers=AUTH)

        assert len(response.json()["user_level"]["recent_sets"]) == 5

    def test_user_level_present_even_without_weight(self, client, seeded_db, fake_google, mock_db):
        """User level is embedded even when weight_kg is missing (muscle load stays null)."""
        _seed_user(mock_db, weight_kg=None)
        fake_google.set_user(google_payload())

        response = client.get("/exercises/pushups_level_1", headers=AUTH)

        body = response.json()
        assert body["muscle_load_by_difficulty"] is None
        assert body["user_level"] is not None
        assert body["user_level"]["level"] == "beginner"

