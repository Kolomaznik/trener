import pytest

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

SESSION_PAYLOAD = {
    "exercise_id": "pushups_level_1",
    "exercise_name": "Kliky o zeď",
    "started_at": "2026-05-03T10:00:00Z",
    "total_duration_sec": 60.0,
    "total_reps": 15,
    "counting": [],
    "set_number": 1,
}


@pytest.fixture
def authed_client(client, fake_google):
    fake_google.set_user(google_payload())
    client.get("/user/settings", headers=AUTH)
    fake_google.set_user(google_payload())
    return client


def _seed_pushups_level_1(mock_db):
    mock_db["exercises"].insert_one(
        {
            "_id": "pushups_level_1",
            "name": "pushups_level_1",
            "title": "Kliky o zeď",
            "family": "Kliky",
            "level": 1,
            "cadence": {
                "eccentric_sec": 2,
                "pause_bottom_sec": 0,
                "concentric_sec": 1,
                "pause_top_sec": 0,
                "total_rep_time_sec": 3,  # matches the 1 s/rep counting in _payload_with_reps
                "coach_note": "",
            },
            "progression_goals": {
                "beginner": {"sets": 1, "reps": 10},
                "intermediate": {"sets": 2, "reps": 25},
                "mastery": {"sets": 3, "reps": 50},
            },
            "muscle_engagement_percent": {"chest": 40},
            "level_coefficient": 0.2,
            "height_multiplier": 0.4,
        }
    )


def _add_pushups_for_user(authed_client, fake_google):
    """The user must have added the exercise before any workout-session POST."""
    fake_google.set_user(google_payload())
    response = authed_client.post(
        "/user-exercises",
        json={"exercise_name": "pushups_level_1"},
        headers=AUTH,
    )
    assert response.status_code == 201, response.text


def _payload_with_reps(total_reps: int, *, set_number: int = 1) -> dict:
    return {
        "exercise_id": "pushups_level_1",
        "exercise_name": "Kliky o zeď",
        "started_at": "2026-05-03T10:00:00Z",
        "total_duration_sec": 60.0,
        "total_reps": total_reps,
        "set_number": set_number,
        "counting": [
            {
                "value": i,
                "token": str(i),
                "timestamp_ms": 10_000 + 1_000 * i,
                "timestamp_iso": f"2026-05-03T10:00:{i:02d}Z",
                "interpolated": False,
            }
            for i in range(1, total_reps + 1)
        ],
    }


def test_post_exercise_series_returns_400_when_exercise_not_added(authed_client, mock_db):
    """Auto-creation removed: posting for an unadded exercise must fail."""
    _seed_pushups_level_1(mock_db)

    response = authed_client.post("/exercise-series", json=SESSION_PAYLOAD, headers=AUTH)
    assert response.status_code == 400
    assert "Cviky (katalog)" in response.json()["detail"]
    assert mock_db["user_exercises"].count_documents({}) == 0


def test_post_exercise_series_returns_201(authed_client, mock_db, fake_google):
    _seed_pushups_level_1(mock_db)
    _add_pushups_for_user(authed_client, fake_google)
    fake_google.set_user(google_payload())

    response = authed_client.post("/exercise-series", json=SESSION_PAYLOAD, headers=AUTH)
    assert response.status_code == 201


def test_post_exercise_series_refreshes_user_exercises(authed_client, mock_db, fake_google):
    _seed_pushups_level_1(mock_db)
    _add_pushups_for_user(authed_client, fake_google)
    fake_google.set_user(google_payload())

    response = authed_client.post("/exercise-series", json=SESSION_PAYLOAD, headers=AUTH)
    assert response.status_code == 201

    user_exercise = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert user_exercise is not None
    # The slim row carries only intrinsic state — no best_result/recent_sets
    # caches anymore. The submitted (zero-rep, below-target) session is a
    # streak failure, but since the streak was never started no
    # consecutive_successes field is written.
    assert user_exercise["user_level"] == "beginner"
    assert "consecutive_successes" not in user_exercise
    assert "best_result" not in user_exercise
    assert "recent_sets" not in user_exercise


def test_exercise_series_persists_evaluation_and_user_level(
    authed_client,
    mock_db,
    fake_google,
):
    """Each series doc carries the calculated evaluation block and the
    user_level snapshot at the moment of saving. target_reps is no
    longer cached on the row — it's derivable from exercise_id +
    user_level via the catalog's progression_goals."""
    _seed_pushups_level_1(mock_db)
    _add_pushups_for_user(authed_client, fake_google)
    fake_google.set_user(google_payload())

    response = authed_client.post(
        "/exercise-series",
        json=_payload_with_reps(12),
        headers=AUTH,
    )
    assert response.status_code == 201

    series = list(mock_db["exercise_series"].find({"user_email": "alice@example.com"}))
    assert len(series) == 1
    doc = series[0]

    # Snapshot of the user's tier at the time of the set.
    assert doc["user_level"] == "beginner"

    # Evaluation block is persisted — see SetEvaluation in fitness_math.
    assert doc["evaluation"] is not None
    assert doc["evaluation"]["repetition_label"] == "completed"  # 12 >= 10
    assert "pace_label" in doc["evaluation"]

    # The slim v2 shape has no snapshot fields.
    for forbidden in (
        "user_weight_kg",
        "user_height_cm",
        "muscle_engagement_percent",
        "exercise_name",
        "saved_at",
        "target_reps",
    ):
        assert forbidden not in doc, f"{forbidden} should not be stored on exercise_series"


def test_single_above_target_set_does_not_advance_level(authed_client, mock_db, fake_google):
    """Regression for the 'level jumps after one good set' bug.

    The user is a fresh beginner (target 10 reps). One set of 12 ticks the
    streak to 1 but must NOT advance ``user_level``.
    """
    _seed_pushups_level_1(mock_db)
    _add_pushups_for_user(authed_client, fake_google)
    fake_google.set_user(google_payload())

    response = authed_client.post(
        "/exercise-series",
        json=_payload_with_reps(12),
        headers=AUTH,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["level_up"] is None
    assert body["total_reps"] == 12

    user_exercise = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert user_exercise["user_level"] == "beginner"
    assert user_exercise["consecutive_successes"] == 1


def test_three_above_target_sets_advance_level_exactly_once(authed_client, mock_db, fake_google):
    """Three above-target sets in a row advance the user once, then reset
    the streak."""
    _seed_pushups_level_1(mock_db)
    _add_pushups_for_user(authed_client, fake_google)

    final_body = None
    for set_number in range(1, 4):
        fake_google.set_user(google_payload())
        response = authed_client.post(
            "/exercise-series",
            json=_payload_with_reps(12, set_number=set_number),
            headers=AUTH,
        )
        assert response.status_code == 201
        final_body = response.json()

    assert final_body is not None
    assert final_body["level_up"] is not None
    assert final_body["level_up"]["previous_level"] == "beginner"
    assert final_body["level_up"]["new_level"] == "intermediate"

    user_exercise = mock_db["user_exercises"].find_one(
        {"user_email": "alice@example.com", "exercise_name": "pushups_level_1"}
    )
    assert user_exercise["user_level"] == "intermediate"
    assert user_exercise["consecutive_successes"] == 0
