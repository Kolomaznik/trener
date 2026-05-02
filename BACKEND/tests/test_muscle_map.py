import json

from config import settings


def expected_muscle_ids() -> list[str]:
    data = json.loads(settings.muscle_map_json_path.read_text(encoding="utf-8"))
    return [group["id"] for group in data["highlightableMuscleGroups"]]


def test_muscle_map_data_returns_entry_for_every_group_in_json(client):
    expected = expected_muscle_ids()
    assert expected, "muscle-map.json must list at least one group"

    response = client.get("/muscle-map/data")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == set(expected)
    for muscle_id in expected:
        assert body[muscle_id] == {"strength": 0, "increment_since_last_exercise": 0}
