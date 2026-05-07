from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.services.fitness_math import (
    SetEvaluation,
    compute_level,
    evaluate_set_performance,
    interpolate_missing_reps,
)
from app.services.user_exercises import refresh_user_exercise

router = APIRouter(prefix="/workout-sessions", tags=["workout-sessions"])


class WorkoutEvent(BaseModel):
    value: int
    token: str
    timestamp_ms: int
    timestamp_iso: str
    interpolated: bool = False


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
    total_reps: int
    evaluation: SetEvaluation | None = None


@router.post("", response_model=WorkoutSessionCreated, status_code=status.HTTP_201_CREATED)
async def create_workout_session(
    payload: WorkoutSessionCreate = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> WorkoutSessionCreated:
    user_doc = (await db["users"].find_one({"email": user.email})) or {}
    exercise_doc = (await db["exercises"].find_one({"name": payload.exercise_id})) or {}

    # Correct rep count by interpolating over speech-recognition gaps
    session_start_ms = int(payload.started_at.timestamp() * 1000)
    raw_events = [e.model_dump() for e in payload.events]
    corrected_events, corrected_total_reps = interpolate_missing_reps(raw_events, session_start_ms)

    # Evaluate set performance (pace + trend) when cadence data is available.
    # The user's target rep count for this exercise — derived from their level
    # against the exercise's progression goals — is needed so the evaluation
    # can decide whether the set was successfully completed.
    cadence = exercise_doc.get("cadence") or {}
    cadence_total_rep_time_sec: float | None = cadence.get("total_rep_time_sec")
    progression_goals: dict[str, Any] = exercise_doc.get("progression_goals") or {}
    recent_docs = await (
        db["workout_sessions"]
        .find({"user_email": user.email, "exercise_id": payload.exercise_id})
        .sort("started_at", -1)
        .limit(5)
        .to_list(None)
    )
    recent_reps = [d["total_reps"] for d in recent_docs]
    level = compute_level(recent_reps, progression_goals)
    target_reps: int | None = (progression_goals.get(level) or {}).get("reps")
    evaluation = evaluate_set_performance(
        corrected_events,
        cadence_total_rep_time_sec,
        target_reps=target_reps,
        total_reps=corrected_total_reps,
    )

    now = datetime.now(UTC)
    doc: dict[str, Any] = {
        "user_email": user.email,
        "exercise_id": payload.exercise_id,
        "exercise_name": payload.exercise_name,
        "started_at": payload.started_at,
        "ended_at": payload.ended_at,
        "total_duration_sec": payload.total_duration_sec,
        "total_reps": corrected_total_reps,
        "events": corrected_events,
        "set_number": payload.set_number,
        "user_weight_kg": user_doc.get("weight_kg"),
        "user_height_cm": user_doc.get("height_cm"),
        "muscle_engagement_percent": dict(exercise_doc.get("muscle_engagement_percent", {})),
        "saved_at": now,
    }

    result = await db["workout_sessions"].insert_one(doc)
    raw_weight_kg = user_doc.get("weight_kg")
    await refresh_user_exercise(
        db=db,
        user_email=user.email,
        exercise_name=payload.exercise_id,
        weight_kg=float(raw_weight_kg) if raw_weight_kg is not None else None,
    )
    return WorkoutSessionCreated(
        id=str(result.inserted_id),
        total_reps=corrected_total_reps,
        evaluation=evaluation,
    )
