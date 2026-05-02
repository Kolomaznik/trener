def test_list_exercises_returns_six_in_order(client):
    response = client.get("/exercises")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 6
    first = body[0]
    assert first["id"] == "pushups"
    assert first["order"] == 1
    assert first["next_exercise_id"] == "squats"
    assert first["next_exercise_name"] == "Dřepy"
    assert first["available_levels"] == ["beginner", "advanced", "expert"]
    assert body[-1]["id"] == "handstands"
    assert body[-1]["next_exercise_id"] is None
    assert body[-1]["next_exercise_name"] is None


def test_get_exercise_detail_default_level(client):
    response = client.get("/exercises/pushups")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "pushups"
    assert body["level"] == "beginner"
    assert body["level_detail"]["title"] == "Začátečník"
    assert body["level_order"] == ["beginner", "advanced", "expert"]


def test_get_exercise_detail_with_level(client):
    response = client.get("/exercises/squats", params={"level": "expert"})

    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "expert"
    assert body["level_detail"]["title"] == "Expert"


def test_get_exercise_detail_unknown_id_returns_404(client):
    response = client.get("/exercises/neexistuje")

    assert response.status_code == 404
    assert response.json() == {"detail": "Exercise not found"}
