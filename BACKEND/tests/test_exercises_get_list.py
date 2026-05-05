def test_get_exercises_returns_200(client):
    response = client.get("/exercises")
    assert response.status_code == 200
