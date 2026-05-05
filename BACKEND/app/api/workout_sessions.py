from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, status
from pymongo.database import Database

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.schemas.workout_sessions import (
    WorkoutSessionCreate,
    WorkoutSessionResponse,
)

router = APIRouter(prefix="/workout-sessions", tags=["workout-sessions"])


def _compute_level(recent_reps: list[int], progression_goals: dict[str, Any] | None) -> str:
    if not recent_reps or not progression_goals:
        return "beginner"
    avg = sum(recent_reps) / len(recent_reps)
    mastery_reps = (progression_goals.get("mastery") or {}).get("reps", 0)
    beginner_reps = (progression_goals.get("beginner") or {}).get("reps", 0)
    if avg >= mastery_reps:
        return "mastery"
    if avg >= beginner_reps:
        return "intermediate"
    return "beginner"


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
