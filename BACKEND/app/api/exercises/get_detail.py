from datetime import UTC, date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field

from app.auth import GoogleUser, get_optional_user
from app.db import SCHEMA_FILTER, get_db, get_user_weight_kg
from app.services.fitness_math import (
    REST_SECONDS,
    MuscleEngagement,
    SetEvaluation,
    calculate_muscle_load,
)
from app.services.user_exercises import PROGRESSION_LEVELS, _normalize_progression_level
from app.sql_db import get_pool


def _intervals_from_counting(counting: list[dict]) -> list[int]:
    """Diff of consecutive ``timestamp_ms`` values — the inter-rep intervals
    the frontend's IntervalSparkline expects."""
    timestamps = [e["timestamp_ms"] for e in counting if "timestamp_ms" in e]
    return [b - a for a, b in zip(timestamps, timestamps[1:], strict=False)]


router = APIRouter(prefix="/exercises", tags=["exercises"])


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


class LevelSet(BaseModel):
    total_reps: int
    started_at: datetime
    set_number: int
    is_completed: bool | None = None


class TodaySet(BaseModel):
    set_number: int
    total_reps: int
    total_duration_sec: float
    started_at: datetime
    intervals_ms: list[int]
    evaluation: SetEvaluation | None = None


class UserLevelInfo(BaseModel):
    level: str
    level_sets: list[LevelSet]
    today_sets: list[TodaySet]
    today_date: date
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
    pool: AsyncConnectionPool = Depends(get_pool),
    user: GoogleUser | None = Depends(get_optional_user),
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

    if user is not None:
        user_exercise = await db["user_exercises"].find_one(
            {"user_email": user.email, "exercise_name": exercise_name}
        )
        if user_exercise is not None:
            level = _normalize_progression_level(user_exercise.get("user_level")) or "beginner"
            progression_goals: dict[str, Any] = exercise_doc.get("progression_goals") or {}
            goal = progression_goals.get(level) or {}

            # All sets at the user's current level (chronological) + best
            # result across all levels + today's sets (full detail for the
            # frontend's CompletedSetCard rehydration), derived from
            # exercise_series in a single $facet pipeline. Rows without
            # `user_level` (recorded before that field was added) are
            # excluded from level_sets.
            today_date = datetime.now(UTC).date()
            today_start_utc = datetime.combine(today_date, time.min, tzinfo=UTC)
            facet_rows = await (
                db["exercise_series"]
                .aggregate(
                    [
                        {
                            "$match": {
                                "user_email": user.email,
                                "exercise_id": exercise_name,
                            }
                        },
                        {
                            "$facet": {
                                "level_sets": [
                                    {"$match": {"user_level": level}},
                                    {"$sort": {"started_at": 1}},
                                    {
                                        "$project": {
                                            "_id": 0,
                                            "total_reps": 1,
                                            "started_at": 1,
                                            "set_number": 1,
                                            "is_completed": "$evaluation.is_completed",
                                        }
                                    },
                                ],
                                "today": [
                                    {"$match": {"started_at": {"$gte": today_start_utc}}},
                                    {"$sort": {"started_at": 1}},
                                    {
                                        "$project": {
                                            "_id": 0,
                                            "set_number": 1,
                                            "total_reps": 1,
                                            "total_duration_sec": 1,
                                            "started_at": 1,
                                            "counting": 1,
                                            "evaluation": 1,
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
            facet = facet_rows[0] if facet_rows else {"level_sets": [], "today": [], "best": []}
            level_sets = [LevelSet(**rs) for rs in facet.get("level_sets", [])]
            today_sets = [
                TodaySet(
                    set_number=row["set_number"],
                    total_reps=row["total_reps"],
                    total_duration_sec=row["total_duration_sec"],
                    started_at=row["started_at"],
                    intervals_ms=_intervals_from_counting(row.get("counting") or []),
                    evaluation=(
                        SetEvaluation(**row["evaluation"]) if row.get("evaluation") else None
                    ),
                )
                for row in facet.get("today", [])
            ]
            best_rows = facet.get("best") or []
            last_best_reps = best_rows[0]["best_result"] if best_rows else None

            user_level = UserLevelInfo(
                level=level,
                level_sets=level_sets,
                today_sets=today_sets,
                today_date=today_date,
                target_reps=goal.get("reps"),
                target_sets=goal.get("sets"),
                last_best_reps=last_best_reps,
                rest_seconds=REST_SECONDS.get(level, 60),
            )

            muscle_engagement_percent: dict[str, int] = (
                exercise_doc.get("muscle_engagement_percent") or {}
            )
            level_coefficient: float = exercise_doc.get("level_coefficient", 0.5)
            weight_kg = await get_user_weight_kg(pool, user.email)
            mld = _muscle_load_by_difficulty(
                progression_goals=progression_goals,
                muscle_engagement_percent=muscle_engagement_percent,
                level_coefficient=level_coefficient,
                weight_kg=weight_kg,
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
