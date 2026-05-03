"""Tests for new exercise endpoints: family listing and muscle-load calculation."""

import pytest

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


# ── POST /exercises/{id}/muscle-load ─────────────────────────────────────────

VALID_PAYLOAD = {
    "weight_kg": 80.0,
    "height_cm": 175.0,
    "age": 25,
    "gender": "M",
    "total_reps": 10,
}


def test_muscle_load_returns_engagement(client, seeded_db):
    response = client.post("/exercises/pushups_level_1/muscle-load", json=VALID_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert "muscle_engagement" in body
    engagement = body["muscle_engagement"]
    assert "chest" in engagement
    assert engagement["chest"]["percent"] == 40
    assert isinstance(engagement["chest"]["muscle_load"], int)
    assert engagement["chest"]["muscle_load"] > 0


def test_muscle_load_correct_formula(client, seeded_db):
    """Verify formula: h=1.75*0.40=0.70, W=80*9.81*0.70*10*0.20, C_phys=1.0"""
    response = client.post("/exercises/pushups_level_1/muscle-load", json=VALID_PAYLOAD)

    h = 1.75 * 0.40
    w = 80 * 9.81 * h * 10 * 0.20
    expected_chest = round(w * 1.0 * 40 / 100)

    assert response.json()["muscle_engagement"]["chest"]["muscle_load"] == expected_chest


def test_muscle_load_404_unknown_exercise(client, seeded_db):
    response = client.post("/exercises/neexistuje/muscle-load", json=VALID_PAYLOAD)

    assert response.status_code == 404


def test_muscle_load_validation_rejects_bad_gender(client, seeded_db):
    bad_payload = {**VALID_PAYLOAD, "gender": "X"}
    response = client.post("/exercises/pushups_level_1/muscle-load", json=bad_payload)

    assert response.status_code == 422


def test_muscle_load_validation_rejects_zero_reps(client, seeded_db):
    bad_payload = {**VALID_PAYLOAD, "total_reps": 0}
    response = client.post("/exercises/pushups_level_1/muscle-load", json=bad_payload)

    assert response.status_code == 422


def test_muscle_load_female_higher_than_male(client, seeded_db):
    male = client.post(
        "/exercises/pushups_level_1/muscle-load",
        json={**VALID_PAYLOAD, "gender": "M"},
    ).json()["muscle_engagement"]["chest"]["muscle_load"]

    female = client.post(
        "/exercises/pushups_level_1/muscle-load",
        json={**VALID_PAYLOAD, "gender": "F"},
    ).json()["muscle_engagement"]["chest"]["muscle_load"]

    assert female > male
