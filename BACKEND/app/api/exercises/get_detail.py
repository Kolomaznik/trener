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
    compute_level,
)
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


@router.get("/{exercise_name}", response_model=ExerciseDetailResponse)
async def get_exercise_detail(
    exercise_name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user_context: _UserContext = Depends(_get_optional_user_context),
) -> ExerciseDetailResponse:
    doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if doc is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    nxt = await db["exercises"].find_one({"family": doc["family"], "level": doc["level"] + 1})

    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None
    user_level: UserLevelInfo | None = None

    if user_context.email is not None:
        if user_context.weight_kg is not None:
            level_coefficient: float = doc.get("level_coefficient", 0.5)
            muscle_engagement: dict[str, int] = dict(doc.get("muscle_engagement_percent", {}))
            progression: dict[str, Any] = doc.get("progression_goals") or {}
            tiers: dict[str, dict] = {}
            for tier in ("beginner", "intermediate", "mastery"):
                goal = progression.get(tier)
                if goal and muscle_engagement:
                    total_reps = int(goal.get("sets", 1)) * int(goal.get("reps", 1))
                    tiers[tier] = calculate_muscle_load(
                        weight_kg=user_context.weight_kg,
                        total_reps=total_reps,
                        level_coefficient=level_coefficient,
                        muscle_engagement_percent=muscle_engagement,
                    )
                else:
                    tiers[tier] = {}
            muscle_load_by_difficulty = MuscleLoadByDifficulty(
                beginner=tiers["beginner"],
                intermediate=tiers["intermediate"],
                mastery=tiers["mastery"],
            )

        recent_docs = await (
            db["workout_sessions"]
            .find({"user_email": user_context.email, "exercise_id": exercise_name})
            .sort("started_at", -1)
            .limit(5)
            .to_list(None)
        )
        progression_goals: dict[str, Any] | None = doc.get("progression_goals")
        recent_reps = [d["total_reps"] for d in recent_docs]
        level = compute_level(recent_reps, progression_goals)

        recent_sets = [
            RecentSet(
                total_reps=d["total_reps"],
                started_at=d["started_at"],
                set_number=d["set_number"],
            )
            for d in recent_docs
        ]

        target_reps: int | None = None
        target_sets: int | None = None
        if progression_goals:
            goal = progression_goals.get(level) or {}
            target_reps = goal.get("reps")
            target_sets = goal.get("sets")

        last_best_reps = max(recent_reps) if recent_reps else None
        user_level = UserLevelInfo(
            level=level,
            recent_sets=recent_sets,
            target_reps=target_reps,
            target_sets=target_sets,
            last_best_reps=last_best_reps,
            rest_seconds=REST_SECONDS.get(level, 60),
        )

    media_doc = doc.get("media") if isinstance(doc.get("media"), dict) else None
    cadence_doc = doc.get("cadence") if isinstance(doc.get("cadence"), dict) else None
    progression_doc = (
        doc.get("progression_goals") if isinstance(doc.get("progression_goals"), dict) else None
    )

    return ExerciseDetailResponse(
        name=doc["name"],
        title=doc["title"],
        english_name=doc.get("english_name"),
        family=doc["family"],
        level=doc["level"],
        description=doc.get("description", ""),
        media=dict(media_doc) if media_doc else None,
        cadence=Cadence(**cadence_doc) if cadence_doc else None,
        progression_goals=ProgressionGoals(**progression_doc) if progression_doc else None,
        muscle_engagement_percent=dict(doc.get("muscle_engagement_percent", {})),
        level_coefficient=doc.get("level_coefficient", 0.5),
        height_multiplier=doc.get("height_multiplier", 0.5),
        next_exercise_name=nxt["name"] if nxt else None,
        next_exercise_title=nxt["title"] if nxt else None,
        muscle_load_by_difficulty=muscle_load_by_difficulty,
        user_level=user_level,
    )
