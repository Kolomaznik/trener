import pytest

PUSHUPS_LEVEL_1 = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "english_name": "Wall Push-ups",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační a přípravný cvik.",
    "instructions": [
        "Postav se čelem ke zdi.",
        "Polož dlaně na zeď ve výšce hrudníku.",
    ],
    "media": {
        "youtube_tutorial": "https://www.youtube.com/watch?v=a6YHbNXW09k",
        "thumbnail_url": "https://img.youtube.com/vi/a6YHbNXW09k/hqdefault.jpg",
    },
    "cadence": {
        "eccentric_sec": 2,
        "pause_bottom_sec": 1,
        "concentric_sec": 2,
        "pause_top_sec": 1,
        "total_rep_time_sec": 6,
        "coach_note": "Plynulý pohyb.",
    },
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 25},
        "mastery": {"sets": 3, "reps": 50},
        "coach_note": "Po zvládnutí mastery na level 2.",
    },
    "muscle_engagement_percent": {
        "chest": 40,
        "triceps": 30,
        "deltoids": 15,
        "abs": 5,
        "lower_back": 5,
        "hands": 5,
    },
}

PUSHUPS_LEVEL_2 = {
    "_id": "pushups_level_2",
    "id": "pushups_level_2",
    "name": "Kliky v předklonu",
    "family": "Kliky",
    "level": 2,
    "description": "Mírně náročnější varianta klikové progrese.",
    "instructions": ["Opři se o lavici nebo schody."],
    "progression_goals": {
        "beginner": {"sets": 1, "reps": 10},
        "intermediate": {"sets": 2, "reps": 20},
        "mastery": {"sets": 3, "reps": 40},
        "coach_note": "Po zvládnutí pokračuj na level 3.",
    },
    "muscle_engagement_percent": {"chest": 50, "triceps": 30, "deltoids": 15, "abs": 5},
}

SQUATS_LEVEL_1 = {
    "_id": "squats_level_1",
    "id": "squats_level_1",
    "name": "Dřep o židli",
    "family": "Dřepy",
    "level": 1,
    "description": "Základní rehabilitační dřep.",
    "instructions": ["Posaď se a postav."],
}

LEGACY_PLACEHOLDER = {
    "_id": "squat",
    "name": "Squat",
    "category": "legs",
}


@pytest.fixture
def seeded_db(mock_db):
    mock_db["exercises"].insert_many(
        [PUSHUPS_LEVEL_1, PUSHUPS_LEVEL_2, SQUATS_LEVEL_1, LEGACY_PLACEHOLDER]
    )
    return mock_db


def test_list_returns_only_full_schema_records(client, seeded_db):
    response = client.get("/exercises")

    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body]
    assert ids == ["squats_level_1", "pushups_level_1", "pushups_level_2"]
    assert "squat" not in ids


def test_list_includes_next_exercise_within_family(client, seeded_db):
    response = client.get("/exercises")

    by_id = {item["id"]: item for item in response.json()}
    assert by_id["pushups_level_1"]["next_exercise_id"] == "pushups_level_2"
    assert by_id["pushups_level_1"]["next_exercise_name"] == "Kliky v předklonu"
    assert by_id["pushups_level_2"]["next_exercise_id"] is None
    assert by_id["squats_level_1"]["next_exercise_id"] is None


def test_detail_returns_full_payload(client, seeded_db):
    response = client.get("/exercises/pushups_level_1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "pushups_level_1"
    assert body["name"] == "Kliky o zeď"
    assert body["english_name"] == "Wall Push-ups"
    assert body["family"] == "Kliky"
    assert body["level"] == 1
    assert body["instructions"][0].startswith("Postav se")
    assert body["cadence"]["total_rep_time_sec"] == 6
    assert body["progression_goals"]["mastery"]["reps"] == 50
    assert body["muscle_engagement_percent"]["chest"] == 40
    assert body["media"]["youtube_tutorial"].startswith("https://www.youtube.com")
    assert body["next_exercise_id"] == "pushups_level_2"
    assert body["next_exercise_name"] == "Kliky v předklonu"


def test_detail_with_optional_fields_missing(client, seeded_db):
    response = client.get("/exercises/squats_level_1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "squats_level_1"
    assert body["cadence"] is None
    assert body["progression_goals"] is None
    assert body["media"] is None
    assert body["muscle_engagement_percent"] == {}
    assert body["next_exercise_id"] is None


def test_detail_unknown_id_returns_404(client, seeded_db):
    response = client.get("/exercises/neexistuje")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exercise not found"}


def test_detail_legacy_placeholder_is_not_found(client, seeded_db):
    response = client.get("/exercises/squat")

    assert response.status_code == 404


def test_list_is_empty_when_db_empty(client, mock_db):
    response = client.get("/exercises")

    assert response.status_code == 200
    assert response.json() == []
