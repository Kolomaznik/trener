from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, status
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/workout-sessions", tags=["workout-sessions"])


class WorkoutEvent(BaseModel):
    value: int
    token: str
    timestamp_ms: int
    timestamp_iso: str


class WorkoutSessionCreate(BaseModel):
    exercise_id: str
    exercise_name: str
    started_at: datetime
    ended_at: datetime
    total_duration_sec: float = Field(ge=0)
    total_reps: int = Field(ge=0)
    events: list[WorkoutEvent] = Field(default_factory=list)
    set_number: int = Field(ge=1)


class WorkoutSessionCreated(BaseModel):
    id: str


@router.post("", response_model=WorkoutSessionCreated, status_code=status.HTTP_201_CREATED)
def create_workout_session(
    payload: WorkoutSessionCreate = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> WorkoutSessionCreated:
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
    return WorkoutSessionCreated(id=str(result.inserted_id))
