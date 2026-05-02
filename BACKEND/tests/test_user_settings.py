from datetime import datetime

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


def test_get_first_call_creates_user_with_full_google_profile(client, mock_db, fake_google):
    fake_google.set_user(google_payload(custom_unknown="surprise"))

    response = client.get("/user/settings", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["name"] == "Alice Example"
    assert body["gender"] is None
    assert body["height_cm"] is None
    assert body["weight_kg"] is None
    assert body["birth_year"] is None

    doc = mock_db["users"].find_one({"email": "alice@example.com"})
    assert doc is not None
    for field in ("sub", "email_verified", "given_name", "family_name", "picture", "locale", "hd"):
        assert field in doc, f"missing {field} in mongo doc"
    assert doc["custom_unknown"] == "surprise"
    assert isinstance(doc["created_at"], datetime)


def test_get_second_call_refreshes_google_fields_and_keeps_user_set_fields(
    client,
    mock_db,
    fake_google,
):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    mock_db["users"].update_one(
        {"email": "alice@example.com"},
        {"$set": {"gender": "female", "height_cm": 170, "weight_kg": 65.5, "birth_year": 1990}},
    )

    fake_google.set_user(google_payload(name="Alice Renamed", picture="https://x/new.jpg"))
    response = client.get("/user/settings", headers=AUTH)

    body = response.json()
    assert body["name"] == "Alice Renamed"
    assert body["gender"] == "female"
    assert body["height_cm"] == 170
    assert body["weight_kg"] == 65.5
    assert body["birth_year"] == 1990

    docs = list(mock_db["users"].find({"email": "alice@example.com"}))
    assert len(docs) == 1, "second call must not create a duplicate"


def test_get_without_auth_returns_401(client):
    response = client.get("/user/settings")
    assert response.status_code in (401, 403)


def test_patch_partial_update_only_changes_given_field(client, mock_db, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"gender": "male"}, headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["gender"] == "male"
    assert body["height_cm"] is None
    assert body["weight_kg"] is None
    assert body["birth_year"] is None


def test_patch_multiple_fields_in_one_call(client, mock_db, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch(
        "/user/settings",
        json={"gender": "female", "height_cm": 168, "weight_kg": 58.2, "birth_year": 1995},
        headers=AUTH,
    )
    body = response.json()
    assert body["gender"] == "female"
    assert body["height_cm"] == 168
    assert body["weight_kg"] == 58.2
    assert body["birth_year"] == 1995


def test_patch_rejects_unknown_field(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"role": "admin"}, headers=AUTH)
    assert response.status_code == 422


def test_patch_validates_height_range(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"height_cm": 10}, headers=AUTH)
    assert response.status_code == 422

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"height_cm": 999}, headers=AUTH)
    assert response.status_code == 422


def test_patch_validates_weight_range(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"weight_kg": 1.0}, headers=AUTH)
    assert response.status_code == 422

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"weight_kg": 1000.0}, headers=AUTH)
    assert response.status_code == 422


def test_patch_validates_birth_year_range(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"birth_year": 1700}, headers=AUTH)
    assert response.status_code == 422


def test_patch_rejects_unknown_gender(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.patch("/user/settings", json={"gender": "other"}, headers=AUTH)
    assert response.status_code == 422


def test_patch_without_auth_returns_401(client):
    response = client.patch("/user/settings", json={"gender": "male"})
    assert response.status_code in (401, 403)
