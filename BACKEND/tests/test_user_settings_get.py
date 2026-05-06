from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


def test_get_user_settings_returns_200(client, fake_google):
    fake_google.set_user(google_payload())
    response = client.get("/user/settings", headers=AUTH)
    assert response.status_code == 200
