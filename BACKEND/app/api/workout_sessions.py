from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, status
from pymongo.database import Database

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.schemas.workout_sessions import (
    RecentSet,
    UserLevelInfo,
    WorkoutSessionCreate,
    WorkoutSessionResponse,
)
from app.services.fitness_math import REST_SECONDS, compute_level

router = APIRouter(prefix="/workout-sessions", tags=["workout-sessions"])


@router.post("", response_model=WorkoutSessionResponse, status_code=status.HTTP_201_CREATED)
def create_workout_session(
    payload: WorkoutSessionCreate = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> WorkoutSessionResponse:
    user_doc = db["users"].find_one({"email": user.email}) or {}
    exercise_doc = db["exercises"].find_one({"id": payload.exercise_id}) or {}

    now = datetime.now(UTC)
    doc: dict[str, Any] = {
        "user_email": user.email,
        "exercise_id": payload.exercise_id,
        "exercise_name": payload.exercise_name,
        "started_at": payload.started_at,
        "ended_at": payload.ended_at,
        "total_duration_sec": payload.total_duration_sec,
        "total_reps": payload.total_reps,
        "events": [e.model_dump() for e in payload.events],
        "set_number": payload.set_number,
        "user_weight_kg": user_doc.get("weight_kg"),
        "user_height_cm": user_doc.get("height_cm"),
        "muscle_engagement_percent": dict(exercise_doc.get("muscle_engagement_percent", {})),
        "saved_at": now,
    }

    result = db["workout_sessions"].insert_one(doc)

    return WorkoutSessionResponse(
        id=str(result.inserted_id),
        **{k: v for k, v in doc.items() if k != "_id"},
    )


@router.get("/level/{exercise_id}", response_model=UserLevelInfo)
def get_user_level(
    exercise_id: str,
    user: GoogleUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> UserLevelInfo:
    recent_docs = list(
        db["workout_sessions"]
        .find({"user_email": user.email, "exercise_id": exercise_id})
        .sort("started_at", -1)
        .limit(5)
    )

    exercise_doc = db["exercises"].find_one({"id": exercise_id}) or {}
    progression_goals = exercise_doc.get("progression_goals")

    recent_reps = [doc["total_reps"] for doc in recent_docs]
    level = compute_level(recent_reps, progression_goals)

    recent_sets = [
        RecentSet(
            total_reps=doc["total_reps"],
            started_at=doc["started_at"],
            set_number=doc["set_number"],
        )
        for doc in recent_docs
    ]

    target_reps: int | None = None
    target_sets: int | None = None
    if progression_goals:
        goal = progression_goals.get(level) or {}
        target_reps = goal.get("reps")
        target_sets = goal.get("sets")

    last_best_reps = max(recent_reps) if recent_reps else None

    return UserLevelInfo(
        level=level,
        recent_sets=recent_sets,
        target_reps=target_reps,
        target_sets=target_sets,
        last_best_reps=last_best_reps,
        rest_seconds=REST_SECONDS.get(level, 60),
    )
