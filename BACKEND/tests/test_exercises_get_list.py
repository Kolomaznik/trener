AUTH = {"Authorization": "Bearer dummy-token"}


def _seed_level_one_exercises(mock_db):
    mock_db["exercises"].insert_many(
        [
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
            },
            {
                "_id": "squats_level_1",
                "name": "squats_level_1",
                "title": "Dřepy ve svíčce",
                "family": "Dřepy",
                "level": 1,
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 50},
                },
                "muscle_engagement_percent": {"quadriceps": 40},
            },
            {
                "_id": "hspu_level_1",
                "name": "hspu_level_1",
                "title": "Stojka na hlavě o zeď",
                "family": "Kliky ve stojce",
                "level": 1,
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 30},
                    "intermediate": {"sets": 1, "reps": 60},
                    "mastery": {"sets": 1, "reps": 120},
                },
                "muscle_engagement_percent": {"deltoids": 30},
            },
        ]
    )


def test_get_exercises_catalog_returns_lean_rows_without_auth(client, mock_db):
    """The /exercises/catalog endpoint is the admin table data source.
    No authentication required, returns only (name, title, family, level)
    sorted by family then level."""
    _seed_level_one_exercises(mock_db)

    response = client.get("/exercises/catalog")
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 3
    for item in items:
        assert set(item.keys()) == {"name", "title", "family", "level"}
    families = [item["family"] for item in items]
    assert families == sorted(families)


def test_catalog_does_not_create_user_exercises_rows(client, mock_db):
    """Opening the catalog must not seed any user-specific data, even when
    a Bearer token is present (the endpoint is auth-agnostic)."""
    _seed_level_one_exercises(mock_db)
    mock_db["users"].insert_one({"email": "alice@example.com", "weight_kg": 80.0})

    response = client.get("/exercises/catalog", headers=AUTH)
    assert response.status_code == 200
    items = response.json()
    assert all("user_level" not in item for item in items)
    assert mock_db["user_exercises"].count_documents({}) == 0


def test_legacy_trainee_endpoint_is_gone(client):
    """The /exercises root endpoint was removed. Detail (/exercises/{name})
    and catalog (/exercises/catalog) are the only routes the prefix exposes."""
    response = client.get("/exercises")
    assert response.status_code == 404
