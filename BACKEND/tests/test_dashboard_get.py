from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


def test_get_dashboard_returns_200(client, fake_google):
    fake_google.set_user(google_payload())
    response = client.get("/dashboard", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    assert "year_summary" in payload
    assert "muscle_map" not in payload
