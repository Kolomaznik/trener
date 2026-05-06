from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


def test_patch_user_settings_returns_204(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)
    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"gender": "male"}, headers=AUTH)
    assert response.status_code == 204
