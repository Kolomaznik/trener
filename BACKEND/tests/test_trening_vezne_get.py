from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


def test_get_trening_vezne_returns_200_with_empty_matrix(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    response = client.get("/trening-vezne", headers=AUTH)
    assert response.status_code == 200

    body = response.json()
    assert [f["key"] for f in body["families"]] == [
        "pushups",
        "squats",
        "pullups",
        "legraises",
        "bridges",
        "hspu",
    ]
    assert body["levels"] == list(range(1, 11))

    for family in body["families"]:
        family_cells = body["cells"][family["key"]]
        assert sorted(family_cells.keys(), key=int) == [str(i) for i in range(1, 11)]
        for cell in family_cells.values():
            assert cell == {"stars": 0, "achieved_at": None}

    stored = mock_db["user_achievements"].find_one({"user_email": "alice@example.com"})
    assert stored is not None
    assert set(stored["cells"].keys()) == {
        "pushups",
        "squats",
        "pullups",
        "legraises",
        "bridges",
        "hspu",
    }


def test_get_trening_vezne_is_idempotent(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    client.get("/trening-vezne", headers=AUTH)

    fake_google.set_user(google_payload())
    response = client.get("/trening-vezne", headers=AUTH)
    assert response.status_code == 200

    assert mock_db["user_achievements"].count_documents({"user_email": "alice@example.com"}) == 1
