"""POST /exercise-series — record one finished set.

The endpoint:

1. Validates that the user has explicitly added the exercise (no
   auto-create, see services/user_exercises.py).
2. Runs ``interpolate_missing_reps`` to fill voice-counter gaps and
   produce the corrected ``total_reps``.
3. Looks up the user's current progression tier on the catalog and
   evaluates pace / trend / repetition_label / is_completed.
4. Persists the full series doc — input ``counting`` events,
   calculated ``total_reps``, evaluation result, and the ``user_level``
   snapshot — into the ``exercise_series`` collection. ``target_reps``
   is not stored; it is derivable from ``exercise_id`` plus
   ``user_level`` against the catalog's ``progression_goals``.
5. Calls ``refresh_user_exercise`` to update the streak (no second write
   to ``user_exercises`` if the latest set didn't change progression).

The persisted shape is the contract documented in
``MONGO_DB`` plan file under "exercise_series document schema".
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.services.fitness_math import (
    SetEvaluation,
    evaluate_set_performance,
    interpolate_missing_reps,
)
from app.services.user_exercises import PROGRESSION_LEVELS, LevelUpInfo, refresh_user_exercise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exercise-series", tags=["exercise-series"])


class CountingEvent(BaseModel):
    """One voice-counted rep event. The list of these on the request body
    is named ``counting`` to make the domain meaning explicit on the wire
    and on disk."""

    value: int
    token: str
    timestamp_ms: int
    timestamp_iso: str
    interpolated: bool = False


class ExerciseSeriesCreate(BaseModel):
    exercise_id: str
    started_at: datetime
    total_duration_sec: float = Field(ge=0)
    total_reps: int = Field(ge=0)  # client estimate; server recomputes from counting
    counting: list[CountingEvent] = Field(default_factory=list)
    set_number: int = Field(ge=1)


class ExerciseSeriesCreated(BaseModel):
    id: str
    total_reps: int
    target_reps: int | None = None
    user_level: str
    evaluation: SetEvaluation | None = None
    level_up: LevelUpInfo | None = None


@router.post("", response_model=ExerciseSeriesCreated, status_code=status.HTTP_201_CREATED)
async def create_exercise_series(
    payload: ExerciseSeriesCreate = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ExerciseSeriesCreated:
    exercise_doc = (await db["exercises"].find_one({"name": payload.exercise_id})) or {}

    user_exercise = await db["user_exercises"].find_one(
        {"user_email": user.email, "exercise_name": payload.exercise_id}
    )
    if user_exercise is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tento cvik nemáš přidaný v seznamu. " "Otevři Cviky (katalog) a klikni na Přidat."
            ),
        )

    # Correct rep count by interpolating over speech-recognition gaps.
    session_start_ms = int(payload.started_at.timestamp() * 1000)
    raw_counting = [e.model_dump() for e in payload.counting]
    corrected_counting, corrected_total_reps = interpolate_missing_reps(
        raw_counting, session_start_ms
    )

    # The user's progression level is the ONLY source of truth for which
    # progression_goals tier we evaluate against. We do not recompute it
    # from history here — that's the job of refresh_user_exercise.
    level = user_exercise.get("user_level")
    if level not in PROGRESSION_LEVELS:
        logger.warning(
            "exercise_series: user_exercises row for %s/%s has invalid user_level=%r; "
            "falling back to 'beginner'",
            user.email,
            payload.exercise_id,
            level,
        )
        level = "beginner"

    cadence = exercise_doc.get("cadence") or {}
    cadence_total_rep_time_sec: float | None = cadence.get("total_rep_time_sec")
    progression_goals: dict[str, Any] = exercise_doc.get("progression_goals") or {}
    target_reps: int | None = (progression_goals.get(level) or {}).get("reps")
    evaluation = evaluate_set_performance(
        corrected_counting,
        cadence_total_rep_time_sec,
        target_reps=target_reps,
        total_reps=corrected_total_reps,
    )

    # Persist the full series — input + calculated + evaluation result
    # + user_level snapshot so historical entries stay interpretable
    # after a level-up (target_reps is derivable from exercise_id +
    # user_level against the catalog). Series are immutable once written.
    doc: dict[str, Any] = {
        "user_email": user.email,
        "exercise_id": payload.exercise_id,
        "started_at": payload.started_at,
        "total_duration_sec": payload.total_duration_sec,
        "set_number": payload.set_number,
        "counting": corrected_counting,
        "total_reps": corrected_total_reps,
        "user_level": level,
        "evaluation": evaluation.model_dump() if evaluation is not None else None,
    }
    result = await db["exercise_series"].insert_one(doc)

    level_up = await refresh_user_exercise(
        db=db,
        user_email=user.email,
        exercise_name=payload.exercise_id,
    )
    return ExerciseSeriesCreated(
        id=str(result.inserted_id),
        total_reps=corrected_total_reps,
        target_reps=target_reps,
        user_level=level,
        evaluation=evaluation,
        level_up=level_up,
    )
