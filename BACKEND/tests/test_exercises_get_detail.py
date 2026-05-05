import pytest

EXERCISE_DOC = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační a přípravný cvik.",
    "instructions": [],
}


@pytest.fixture
def seeded_db(mock_db):
    mock_db["exercises"].insert_one(EXERCISE_DOC)
    return mock_db


def test_get_exercise_detail_returns_200(client, seeded_db):
    response = client.get("/exercises/pushups_level_1")
    assert response.status_code == 200
