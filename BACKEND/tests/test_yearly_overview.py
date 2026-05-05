from datetime import UTC, date, datetime

import pytest

from tests.conftest import google_payload

AUTH = {"Authorization": "Bearer dummy-token"}

EXERCISE_DOC = {
    "_id": "pushups_level_1",
    "id": "pushups_level_1",
    "name": "Kliky o zeď",
    "family": "Kliky",
    "level": 1,
    "description": "Rehabilitační cvik.",
    "instructions": [],
    "progression_goals": {},
    "muscle_engagement_percent": {},
}


def _session(user_email: str, started_at: datetime) -> dict:
    return {
        "user_email": user_email,
        "exercise_id": "pushups_level_1",
        "exercise_name": "Kliky o zeď",
        "started_at": started_at,
        "ended_at": started_at,
        "total_duration_sec": 60.0,
        "total_reps": 10,
        "events": [],
        "set_number": 1,
        "saved_at": datetime.now(UTC),
    }


@pytest.fixture
def authed_client(client, fake_google):
    fake_google.set_user(google_payload())
    return client


class TestYearlyOverview:
    def test_requires_auth(self, client):
        response = client.get("/dashboard/yearly-overview")

        assert response.status_code in (401, 403)

    def test_empty_db_returns_all_zeros(self, authed_client, mock_db):
        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "2026-05-05"},
            headers=AUTH,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["end_date"] == "2026-05-05"
        assert all(day["count"] == 0 for day in body["days"])

    def test_counts_sessions_on_correct_day(self, authed_client, mock_db, fake_google):
        mock_db["workout_sessions"].insert_many(
            [
                _session("alice@example.com", datetime(2026, 5, 3, 10, 0, 0)),
                _session("alice@example.com", datetime(2026, 5, 3, 14, 0, 0)),
                _session("alice@example.com", datetime(2026, 5, 4, 9, 0, 0)),
            ]
        )
        fake_google.set_user(google_payload())

        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "2026-05-05"},
            headers=AUTH,
        )

        assert response.status_code == 200
        days_by_date = {d["date"]: d["count"] for d in response.json()["days"]}
        assert days_by_date["2026-05-03"] == 2
        assert days_by_date["2026-05-04"] == 1
        assert days_by_date["2026-05-05"] == 0

    def test_only_counts_current_user_sessions(self, authed_client, mock_db, fake_google):
        mock_db["workout_sessions"].insert_many(
            [
                _session("alice@example.com", datetime(2026, 5, 3, 10, 0, 0)),
                _session("bob@example.com", datetime(2026, 5, 3, 11, 0, 0)),
            ]
        )
        fake_google.set_user(google_payload())

        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "2026-05-05"},
            headers=AUTH,
        )

        assert response.status_code == 200
        days_by_date = {d["date"]: d["count"] for d in response.json()["days"]}
        assert days_by_date["2026-05-03"] == 1

    def test_response_covers_52_weeks(self, authed_client, mock_db, fake_google):
        fake_google.set_user(google_payload())

        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "2026-05-05"},
            headers=AUTH,
        )

        assert response.status_code == 200
        body = response.json()
        start = date.fromisoformat(body["start_date"])
        end = date.fromisoformat(body["end_date"])
        expected_days = (end - start).days + 1
        assert len(body["days"]) == expected_days

    def test_sessions_outside_range_not_counted(self, authed_client, mock_db, fake_google):
        mock_db["workout_sessions"].insert_one(
            _session("alice@example.com", datetime(2020, 1, 1, 10, 0, 0))
        )
        fake_google.set_user(google_payload())

        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "2026-05-05"},
            headers=AUTH,
        )

        assert response.status_code == 200
        assert all(day["count"] == 0 for day in response.json()["days"])

    def test_invalid_end_date_returns_422(self, authed_client, fake_google):
        fake_google.set_user(google_payload())

        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "not-a-date"},
            headers=AUTH,
        )

        assert response.status_code == 422

    def test_count_has_no_upper_bound(self, authed_client, mock_db, fake_google):
        mock_db["workout_sessions"].insert_many(
            [_session("alice@example.com", datetime(2026, 5, 3, i, 0, 0)) for i in range(20)]
        )
        fake_google.set_user(google_payload())

        response = authed_client.get(
            "/dashboard/yearly-overview",
            params={"end_date": "2026-05-05"},
            headers=AUTH,
        )

        assert response.status_code == 200
        days_by_date = {d["date"]: d["count"] for d in response.json()["days"]}
        assert days_by_date["2026-05-03"] == 20
