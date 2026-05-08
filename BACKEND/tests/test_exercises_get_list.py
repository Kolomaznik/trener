import app.api.exercises.get_list as get_list_module
from tests.conftest import FakeAsyncClient, FakeResponse, google_payload

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
                "_id": "pullups_level_1",
                "name": "pullups_level_1",
                "title": "Svislé přítahy",
                "family": "Shyby",
                "level": 1,
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 20},
                    "mastery": {"sets": 3, "reps": 40},
                },
                "muscle_engagement_percent": {"lats": 30},
            },
            {
                "_id": "legraises_level_1",
                "name": "legraises_level_1",
                "title": "Přítahy kolen v sedě",
                "family": "Zdvihy nohou",
                "level": 1,
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 40},
                },
                "muscle_engagement_percent": {"abs": 45},
            },
            {
                "_id": "bridges_level_1",
                "name": "bridges_level_1",
                "title": "Krátké mosty",
                "family": "Mosty",
                "level": 1,
                "progression_goals": {
                    "beginner": {"sets": 1, "reps": 10},
                    "intermediate": {"sets": 2, "reps": 25},
                    "mastery": {"sets": 3, "reps": 50},
                },
                "muscle_engagement_percent": {"glutes": 40},
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


def test_get_exercises_returns_200(client):
    response = client.get("/exercises")
    assert response.status_code == 200


def test_get_exercises_seeds_big5_for_authenticated_user(client, mock_db, monkeypatch):
    _seed_level_one_exercises(mock_db)
    mock_db["users"].insert_one({"email": "alice@example.com", "weight_kg": 80.0})

    FakeAsyncClient.next_response = FakeResponse(200, google_payload())
    FakeAsyncClient.next_exception = None
    monkeypatch.setattr(get_list_module.httpx, "AsyncClient", FakeAsyncClient)

    response = client.get("/exercises", headers=AUTH)
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 5
    assert {item["name"] for item in items} == {
        "pushups_level_1",
        "squats_level_1",
        "pullups_level_1",
        "legraises_level_1",
        "bridges_level_1",
    }
    assert mock_db["user_exercises"].count_documents({"user_email": "alice@example.com"}) == 5
