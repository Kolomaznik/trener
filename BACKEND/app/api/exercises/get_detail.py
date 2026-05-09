from datetime import datetime
from typing import Any, NamedTuple

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.db import get_db
from app.services.fitness_math import (
    REST_SECONDS,
    MuscleEngagement,
    calculate_muscle_load,
)
from app.services.user_exercises import PROGRESSION_LEVELS, _normalize_progression_level
from config import settings as app_settings

router = APIRouter(prefix="/exercises", tags=["exercises"])

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}

_optional_bearer = HTTPBearer(auto_error=False)


class Cadence(BaseModel):
    eccentric_sec: int
    pause_bottom_sec: int
    concentric_sec: int
    pause_top_sec: int
    total_rep_time_sec: int
    coach_note: str


class ProgressionGoal(BaseModel):
    sets: int
    reps: int


class ProgressionGoals(BaseModel):
    beginner: ProgressionGoal
    intermediate: ProgressionGoal
    mastery: ProgressionGoal
    coach_note: str


class MuscleLoadByDifficulty(BaseModel):
    beginner: dict[str, MuscleEngagement] = Field(default_factory=dict)
    intermediate: dict[str, MuscleEngagement] = Field(default_factory=dict)
    mastery: dict[str, MuscleEngagement] = Field(default_factory=dict)


class RecentSet(BaseModel):
    total_reps: int
    started_at: datetime
    set_number: int


class UserLevelInfo(BaseModel):
    level: str
    recent_sets: list[RecentSet]
    target_reps: int | None = None
    target_sets: int | None = None
    last_best_reps: int | None = None
    rest_seconds: int


class ExerciseDetailResponse(BaseModel):
    name: str
    title: str
    english_name: str | None = None
    family: str
    level: int
    description: str
    media: dict[str, str] | None = None
    cadence: Cadence | None = None
    progression_goals: ProgressionGoals | None = None
    muscle_engagement_percent: dict[str, int] = Field(default_factory=dict)
    level_coefficient: float = 0.5
    height_multiplier: float = 0.5
    next_exercise_name: str | None = None
    next_exercise_title: str | None = None
    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None
    user_level: UserLevelInfo | None = None


class _UserContext(NamedTuple):
    email: str | None
    weight_kg: float | None


async def _get_optional_user_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> _UserContext:
    if credentials is None:
        return _UserContext(email=None, weight_kg=None)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                app_settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {credentials.credentials}"},
            )
    except httpx.HTTPError:
        return _UserContext(email=None, weight_kg=None)

    if resp.status_code != 200:
        return _UserContext(email=None, weight_kg=None)

    email = resp.json().get("email")
    if not email:
        return _UserContext(email=None, weight_kg=None)

    user_doc = await db["users"].find_one({"email": email})
    if user_doc is None:
        return _UserContext(email=email, weight_kg=None)

    raw = user_doc.get("weight_kg")
    weight_kg = float(raw) if raw is not None else None
    return _UserContext(email=email, weight_kg=weight_kg)


def _muscle_load_by_difficulty(
    *,
    progression_goals: dict[str, Any],
    muscle_engagement_percent: dict[str, int],
    level_coefficient: float,
    weight_kg: float | None,
) -> dict[str, dict[str, Any]] | None:
    """Compute the per-tier muscle load preview shown on the detail page.

    Used to live on the user_exercises row; now derived inline so the
    row stays state-only.
    """
    if weight_kg is None:
        return None
    tiers: dict[str, dict[str, Any]] = {}
    for tier in PROGRESSION_LEVELS:
        goal = progression_goals.get(tier)
        if not goal:
            tiers[tier] = {}
            continue
        total_reps = int(goal.get("sets", 1)) * int(goal.get("reps", 1))
        calculated = calculate_muscle_load(
            weight_kg=weight_kg,
            total_reps=total_reps,
            level_coefficient=level_coefficient,
            muscle_engagement_percent=muscle_engagement_percent,
        )
        tiers[tier] = {muscle: engagement.model_dump() for muscle, engagement in calculated.items()}
    return tiers


@router.get("/{exercise_name}", response_model=ExerciseDetailResponse)
async def get_exercise_detail(
    exercise_name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user_context: _UserContext = Depends(_get_optional_user_context),
) -> ExerciseDetailResponse:
    # Catalog data (cadence, progression_goals, family, level, …) is the
    # source of truth — always read from `exercises`.
    exercise_doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if exercise_doc is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    next_exercise_doc = await db["exercises"].find_one(
        {"family": exercise_doc["family"], "level": exercise_doc["level"] + 1}
    )

    user_level: UserLevelInfo | None = None
    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None

    if user_context.email is not None:
        user_exercise = await db["user_exercises"].find_one(
            {"user_email": user_context.email, "exercise_name": exercise_name}
        )
        if user_exercise is not None:
            level = _normalize_progression_level(user_exercise.get("user_level")) or "beginner"
            progression_goals: dict[str, Any] = exercise_doc.get("progression_goals") or {}
            goal = progression_goals.get(level) or {}

            # Latest 5 sets + best result, derived from exercise_series
            # in a single $facet pipeline.
            facet_rows = await (
                db["exercise_series"]
                .aggregate(
                    [
                        {
                            "$match": {
                                "user_email": user_context.email,
                                "exercise_id": exercise_name,
                            }
                        },
                        {
                            "$facet": {
                                "recent": [
                                    {"$sort": {"started_at": -1}},
                                    {"$limit": 5},
                                    {
                                        "$project": {
                                            "_id": 0,
                                            "total_reps": 1,
                                            "started_at": 1,
                                            "set_number": 1,
                                        }
                                    },
                                ],
                                "best": [
                                    {
                                        "$group": {
                                            "_id": None,
                                            "best_result": {"$max": "$total_reps"},
                                        }
                                    }
                                ],
                            }
                        },
                    ]
                )
                .to_list(1)
            )
            facet = facet_rows[0] if facet_rows else {"recent": [], "best": []}
            recent_sets = [RecentSet(**rs) for rs in facet.get("recent", [])]
            best_rows = facet.get("best") or []
            last_best_reps = best_rows[0]["best_result"] if best_rows else None

            user_level = UserLevelInfo(
                level=level,
                recent_sets=recent_sets,
                target_reps=goal.get("reps"),
                target_sets=goal.get("sets"),
                last_best_reps=last_best_reps,
                rest_seconds=REST_SECONDS.get(level, 60),
            )

            muscle_engagement_percent: dict[str, int] = (
                exercise_doc.get("muscle_engagement_percent") or {}
            )
            level_coefficient: float = exercise_doc.get("level_coefficient", 0.5)
            mld = _muscle_load_by_difficulty(
                progression_goals=progression_goals,
                muscle_engagement_percent=muscle_engagement_percent,
                level_coefficient=level_coefficient,
                weight_kg=user_context.weight_kg,
            )
            if mld is not None:
                muscle_load_by_difficulty = MuscleLoadByDifficulty(**mld)

    media_doc = exercise_doc.get("media") if isinstance(exercise_doc.get("media"), dict) else None
    cadence_doc = (
        exercise_doc.get("cadence") if isinstance(exercise_doc.get("cadence"), dict) else None
    )
    progression_doc = (
        exercise_doc.get("progression_goals")
        if isinstance(exercise_doc.get("progression_goals"), dict)
        else None
    )

    return ExerciseDetailResponse(
        name=exercise_doc["name"],
        title=exercise_doc["title"],
        english_name=exercise_doc.get("english_name"),
        family=exercise_doc["family"],
        level=exercise_doc["level"],
        description=exercise_doc.get("description", ""),
        media=dict(media_doc) if media_doc else None,
        cadence=Cadence(**cadence_doc) if cadence_doc else None,
        progression_goals=ProgressionGoals(**progression_doc) if progression_doc else None,
        muscle_engagement_percent=dict(exercise_doc.get("muscle_engagement_percent", {})),
        level_coefficient=exercise_doc.get("level_coefficient", 0.5),
        height_multiplier=exercise_doc.get("height_multiplier", 0.5),
        next_exercise_name=next_exercise_doc["name"] if next_exercise_doc else None,
        next_exercise_title=next_exercise_doc["title"] if next_exercise_doc else None,
        muscle_load_by_difficulty=muscle_load_by_difficulty,
        user_level=user_level,
    )
