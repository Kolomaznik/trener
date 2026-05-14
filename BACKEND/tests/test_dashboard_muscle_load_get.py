from datetime import UTC, datetime, timedelta

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}


def _seed_user(mock_db, email="alice@example.com", weight_kg=80.0):
    mock_db["users"].insert_one({"email": email, "weight_kg": weight_kg})


def _seed_exercise(mock_db, name, engagement, level_coefficient=0.5):
    mock_db["exercises"].insert_one(
        {
            "name": name,
            "level": 1,
            "family": "push",
            "muscle_engagement_percent": engagement,
            "level_coefficient": level_coefficient,
        }
    )


def _seed_series(mock_db, *, email, exercise_id, total_reps, started_at):
    mock_db["exercise_series"].insert_one(
        {
            "user_email": email,
            "exercise_id": exercise_id,
            "started_at": started_at,
            "total_reps": total_reps,
        }
    )


def test_muscle_load_defaults_to_week_and_sums_series(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    _seed_user(mock_db)
    _seed_exercise(mock_db, "push-up", {"chest": 60, "triceps": 40})

    now = datetime.now(UTC)
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=20,
        started_at=now - timedelta(days=1),
    )
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=10,
        started_at=now - timedelta(days=2),
    )

    response = client.get("/dashboard/muscle-load", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()

    assert payload["range"] == "week"
    assert payload["series_count"] == 2
    # 80 kg * (20+10) reps * 0.5 coef = 1200 kg total volume
    # chest gets 60% = 720 kg, triceps 40% = 480 kg
    assert payload["muscle_load"]["chest"]["muscle_load"] == 720.0
    assert payload["muscle_load"]["triceps"]["muscle_load"] == 480.0
    assert payload["total_load_kg"] == 1200.0
    assert payload["muscle_load"]["chest"]["percent"] == 100


def test_muscle_load_today_excludes_older_series(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    _seed_user(mock_db)
    _seed_exercise(mock_db, "push-up", {"chest": 60})

    now = datetime.now(UTC)
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=10,
        started_at=now - timedelta(hours=2),
    )
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=99,
        started_at=now - timedelta(days=3),
    )

    response = client.get("/dashboard/muscle-load?range=today", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()

    assert payload["series_count"] == 1
    # 80 kg * 10 reps * 0.5 coef * 60% = 240 kg
    assert payload["muscle_load"]["chest"]["muscle_load"] == 240.0


def test_muscle_load_null_when_user_has_no_weight(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    # No users doc inserted -> weight_kg unknown.

    response = client.get("/dashboard/muscle-load", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    assert payload["muscle_load"] is None


def test_muscle_load_rejects_unknown_range(client, fake_google):
    fake_google.set_user(google_payload())
    response = client.get("/dashboard/muscle-load?range=decade", headers=AUTH)
    assert response.status_code == 422


def test_muscle_series_count_increments_per_series(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    _seed_user(mock_db)
    _seed_exercise(mock_db, "push-up", {"chest": 60, "triceps": 40})
    _seed_exercise(mock_db, "row", {"upper_back": 70, "biceps": 30})

    now = datetime.now(UTC)
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=10,
        started_at=now - timedelta(days=1),
    )
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=10,
        started_at=now - timedelta(days=2),
    )
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="row",
        total_reps=8,
        started_at=now - timedelta(days=3),
    )

    response = client.get("/dashboard/muscle-load", headers=AUTH)
    assert response.status_code == 200
    counts = response.json()["muscle_series_count"]

    assert counts["chest"] == 2
    assert counts["triceps"] == 2
    assert counts["upper_back"] == 1
    assert counts["biceps"] == 1


def test_muscle_series_count_available_without_weight(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    # No users doc -> weight_kg unknown.
    _seed_exercise(mock_db, "push-up", {"chest": 60})
    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=10,
        started_at=datetime.now(UTC) - timedelta(days=1),
    )

    response = client.get("/dashboard/muscle-load", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()

    assert payload["muscle_load"] is None
    assert payload["series_count"] == 1
    assert payload["muscle_series_count"] == {"chest": 1}


def test_muscle_series_count_skips_zero_engagement(client, fake_google, mock_db):
    fake_google.set_user(google_payload())
    _seed_user(mock_db)
    _seed_exercise(mock_db, "push-up", {"chest": 60, "calves": 0})

    _seed_series(
        mock_db,
        email="alice@example.com",
        exercise_id="push-up",
        total_reps=10,
        started_at=datetime.now(UTC) - timedelta(days=1),
    )

    response = client.get("/dashboard/muscle-load", headers=AUTH)
    counts = response.json()["muscle_series_count"]
    assert counts == {"chest": 1}
