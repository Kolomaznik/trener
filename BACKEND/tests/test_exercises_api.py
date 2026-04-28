import mongomock
from fastapi.testclient import TestClient

from app.db.migrations.exercises_seed import transform_source
from app.dependencies import get_exercise_repository
from app.factory import create_app
from app.repositories.exercises import ExerciseRepository

SOURCE_FIXTURE = {
    "kniha": "Test book",
    "cviky": {
        "drepy": [
            {
                "uroven": 1,
                "nazev": "Dřep 1",
                "popis": "První krok. Druhý krok.",
                "svalove_partie": ["kvadricepsy", "Hýždě"],
                "kriteria_vykonu": {"zacatecnik": "1x10"},
                "casovani_tempo": "Tempo 3-1-2-1",
                "odkaz_na_ukazku": "https://example.com/squat-1",
            }
        ]
    },
}


def build_client() -> TestClient:
    app = create_app()
    client = mongomock.MongoClient()
    collection = client["testdb"]["exercises"]
    repository = ExerciseRepository(collection)
    repository.ensure_indexes()
    repository.upsert_many(transform_source(SOURCE_FIXTURE))
    app.dependency_overrides[get_exercise_repository] = lambda: repository
    return TestClient(app)


def test_list_exercises_returns_frontend_schema() -> None:
    client = build_client()

    response = client.get("/api/exercises")

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert {
        "slug",
        "name",
        "category",
        "level",
        "muscle_load",
        "short_description",
        "has_video",
    } <= item.keys()


def test_detail_returns_frontend_schema() -> None:
    client = build_client()
    slug = client.get("/api/exercises").json()["items"][0]["slug"]

    response = client.get(f"/api/exercises/{slug}")

    assert response.status_code == 200
    payload = response.json()
    assert {
        "slug",
        "name",
        "description",
        "muscle_load",
        "performance_criteria",
        "timing",
        "steps",
        "media",
        "progression",
        "metadata",
    } <= payload.keys()


def test_detail_not_found() -> None:
    client = build_client()

    response = client.get("/api/exercises/unknown-slug")

    assert response.status_code == 404
    assert response.json()["detail"] == "Exercise not found"
