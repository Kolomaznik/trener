"""GET /dashboard/muscle-load — per-muscle volume load over a rolling window.

The endpoint sums per-muscle load across every ``exercise_series`` the user
has logged inside the requested window:

* ``today`` — since midnight (UTC) of the current calendar day
* ``week``  — last 7 days
* ``month`` — last 30 days
* ``year``  — last 365 days

Per-series load is computed with :func:`calculate_muscle_load`, the same
formula that drives the per-exercise muscle map on the detail page, so the
two views are directly comparable.

When the user's profile has no ``weight_kg``, ``muscle_load`` is returned
as ``None`` and the frontend shows the same prompt as on the detail page.
"""

from datetime import UTC, datetime, time, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.services.fitness_math import MuscleEngagement, calculate_muscle_load

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RangeKey = Literal["today", "week", "month", "year"]

_RANGE_TO_DAYS: dict[str, int] = {
    "week": 7,
    "month": 30,
    "year": 365,
}


class MuscleLoadResponse(BaseModel):
    range: RangeKey
    start_date: datetime
    end_date: datetime
    series_count: int = Field(ge=0)
    exercise_count: int = Field(ge=0)
    total_reps: int = Field(ge=0)
    total_load_kg: float = Field(ge=0)
    muscle_load: dict[str, MuscleEngagement] | None = None
    # How many distinct exercises in the window engaged each muscle. Computed
    # from ``muscle_engagement_percent`` only — does not depend on
    # ``weight_kg``, so it is populated even for users without a profile weight.
    muscle_exercise_count: dict[str, int] = Field(default_factory=dict)
    # Total reps performed in the window per muscle: every series whose
    # exercise engages the muscle contributes its full ``total_reps``.
    muscle_repetitions: dict[str, int] = Field(default_factory=dict)


async def _user_weight_kg(db: AsyncIOMotorDatabase, email: str) -> float | None:
    user_doc = await db["users"].find_one({"email": email})
    if user_doc is None:
        return None
    raw = user_doc.get("weight_kg")
    return float(raw) if raw is not None else None


@router.get("/muscle-load", response_model=MuscleLoadResponse)
async def get_dashboard_muscle_load(
    range: RangeKey = Query(default="week"),
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MuscleLoadResponse:
    end = datetime.now(UTC)
    if range == "today":
        start = datetime.combine(end.date(), time.min, tzinfo=UTC)
    else:
        start = end - timedelta(days=_RANGE_TO_DAYS[range])

    series = (
        await db["exercise_series"]
        .find(
            {
                "user_email": user.email,
                "started_at": {"$gte": start, "$lte": end},
            },
            {"exercise_id": 1, "total_reps": 1},
        )
        .to_list(None)
    )

    weight_kg = await _user_weight_kg(db, user.email)
    if not series:
        return MuscleLoadResponse(
            range=range,
            start_date=start,
            end_date=end,
            series_count=0,
            exercise_count=0,
            total_reps=0,
            total_load_kg=0.0,
            muscle_load=None if weight_kg is None else {},
            muscle_exercise_count={},
            muscle_repetitions={},
        )

    exercise_ids = {s["exercise_id"] for s in series}
    exercise_docs = (
        await db["exercises"]
        .find(
            {"name": {"$in": list(exercise_ids)}},
            {"name": 1, "muscle_engagement_percent": 1, "level_coefficient": 1},
        )
        .to_list(None)
    )
    by_name: dict[str, dict[str, Any]] = {doc["name"]: doc for doc in exercise_docs}

    # Per-muscle count of distinct exercises that engage it — counted once per
    # exercise, regardless of how many series of it the user logged.
    counts: dict[str, int] = {}
    for ex in by_name.values():
        engagement = ex.get("muscle_engagement_percent") or {}
        for muscle, pct in engagement.items():
            if pct and pct > 0:
                counts[muscle] = counts.get(muscle, 0) + 1

    # Per-muscle total reps — every series whose exercise engages the muscle
    # contributes its full ``total_reps``.
    reps: dict[str, int] = {}
    total_reps = 0
    for s in series:
        series_reps = int(s.get("total_reps", 0))
        total_reps += series_reps
        ex = by_name.get(s["exercise_id"])
        if ex is None:
            continue
        engagement = ex.get("muscle_engagement_percent") or {}
        for muscle, pct in engagement.items():
            if pct and pct > 0:
                reps[muscle] = reps.get(muscle, 0) + series_reps

    totals: dict[str, float] = {}
    if weight_kg is not None:
        for s in series:
            ex = by_name.get(s["exercise_id"])
            if ex is None:
                continue
            engagement = ex.get("muscle_engagement_percent") or {}
            if not engagement:
                continue
            per_muscle = calculate_muscle_load(
                weight_kg=weight_kg,
                total_reps=int(s.get("total_reps", 0)),
                level_coefficient=float(ex.get("level_coefficient", 0.5)),
                muscle_engagement_percent=engagement,
            )
            for muscle, m in per_muscle.items():
                totals[muscle] = totals.get(muscle, 0.0) + m.muscle_load

    if weight_kg is None:
        return MuscleLoadResponse(
            range=range,
            start_date=start,
            end_date=end,
            series_count=len(series),
            exercise_count=len(by_name),
            total_reps=total_reps,
            total_load_kg=0.0,
            muscle_load=None,
            muscle_exercise_count=counts,
            muscle_repetitions=reps,
        )

    if not totals:
        return MuscleLoadResponse(
            range=range,
            start_date=start,
            end_date=end,
            series_count=len(series),
            exercise_count=len(by_name),
            total_reps=total_reps,
            total_load_kg=0.0,
            muscle_load={},
            muscle_exercise_count=counts,
            muscle_repetitions=reps,
        )

    max_load = max(totals.values())
    muscle_load = {
        muscle: MuscleEngagement(
            percent=round((load / max_load) * 100) if max_load > 0 else 0,
            muscle_load=round(load, 1),
        )
        for muscle, load in totals.items()
    }

    return MuscleLoadResponse(
        range=range,
        start_date=start,
        end_date=end,
        series_count=len(series),
        exercise_count=len(by_name),
        total_reps=total_reps,
        total_load_kg=round(sum(totals.values()), 1),
        muscle_load=muscle_load,
        muscle_exercise_count=counts,
        muscle_repetitions=reps,
    )
