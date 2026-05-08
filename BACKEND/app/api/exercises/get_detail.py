from datetime import datetime
from typing import Any, NamedTuple

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.db import get_db
from app.services.fitness_math import REST_SECONDS, MuscleEngagement
from app.services.user_exercises import get_or_seed_user_exercises, refresh_user_exercise
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
    user_level: UserLevelInfo | None = None
    if user_context.email is not None:
        doc = await db["user_exercises"].find_one(
            {"user_email": user_context.email, "exercise_name": exercise_name}
        )
        if doc is None:
            await get_or_seed_user_exercises(db, user_context.email, user_context.weight_kg)
            doc = await db["user_exercises"].find_one(
                {"user_email": user_context.email, "exercise_name": exercise_name}
            )
        if doc is None:
            await refresh_user_exercise(
                db,
                user_context.email,
                exercise_name,
                user_context.weight_kg,
            )
            doc = await db["user_exercises"].find_one(
                {"user_email": user_context.email, "exercise_name": exercise_name}
            )
        if doc is None:
            raise HTTPException(status_code=404, detail="Exercise not found")

        user_level_value = doc.get("user_level")
        if user_level_value:
            user_level = UserLevelInfo(
                level=user_level_value,
                recent_sets=[RecentSet(**recent_set) for recent_set in doc.get("recent_sets", [])],
                target_reps=doc.get("target_reps"),
                target_sets=doc.get("target_sets"),
                last_best_reps=doc.get("best_result"),
                rest_seconds=doc.get("rest_seconds", REST_SECONDS.get(user_level_value, 60)),
            )
    else:
        doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
        if doc is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        nxt = await db["exercises"].find_one({"family": doc["family"], "level": doc["level"] + 1})
        doc = {
            **doc,
            "exercise_name": doc["name"],
            "next_exercise_name": nxt["name"] if nxt else None,
            "next_exercise_title": nxt["title"] if nxt else None,
            "muscle_load_by_difficulty": None,
        }

    media_doc = doc.get("media") if isinstance(doc.get("media"), dict) else None
    cadence_doc = doc.get("cadence") if isinstance(doc.get("cadence"), dict) else None
    progression_doc = (
        doc.get("progression_goals") if isinstance(doc.get("progression_goals"), dict) else None
    )
    muscle_load_doc = (
        doc.get("muscle_load_by_difficulty")
        if isinstance(doc.get("muscle_load_by_difficulty"), dict)
        else None
    )
    muscle_load_by_difficulty = (
        MuscleLoadByDifficulty(**muscle_load_doc) if muscle_load_doc is not None else None
    )

    return ExerciseDetailResponse(
        name=doc["exercise_name"],
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
        next_exercise_name=doc.get("next_exercise_name"),
        next_exercise_title=doc.get("next_exercise_title"),
        muscle_load_by_difficulty=muscle_load_by_difficulty,
        user_level=user_level,
    )
