from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.services.fitness_math import REST_SECONDS
from app.services.user_exercises import (
    UserExerciseAlreadyExists,
    add_user_exercise,
)

router = APIRouter(prefix="/user-exercises", tags=["user-exercises"])


class AddUserExerciseRequest(BaseModel):
    exercise_name: str


class UserExerciseCreated(BaseModel):
    exercise_name: str
    user_level: str
    target_reps: int | None = None
    target_sets: int | None = None
    rest_seconds: int = 60
    created_at: datetime


@router.post("", response_model=UserExerciseCreated, status_code=status.HTTP_201_CREATED)
async def post_user_exercise(
    payload: AddUserExerciseRequest = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserExerciseCreated:
    """Add an exercise from the catalog to the user's personal list.

    * 404 — the requested exercise_name does not exist in the catalog.
    * 409 — the user has already added this exercise.
    """
    try:
        doc: dict[str, Any] = await add_user_exercise(
            db=db,
            user_email=user.email,
            exercise_name=payload.exercise_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UserExerciseAlreadyExists as exc:
        raise HTTPException(
            status_code=409,
            detail=f"already added: {exc}",
        ) from exc

    # The catalog goal for the user's starting tier (always "beginner"
    # right after add) — looked up here rather than cached on the row.
    exercise_doc = await db["exercises"].find_one({"name": payload.exercise_name}) or {}
    progression_goals = exercise_doc.get("progression_goals") or {}
    beginner_goal = progression_goals.get("beginner") or {}

    return UserExerciseCreated(
        exercise_name=doc["exercise_name"],
        user_level=doc["user_level"],
        target_reps=beginner_goal.get("reps"),
        target_sets=beginner_goal.get("sets"),
        rest_seconds=REST_SECONDS.get(doc["user_level"], 60),
        created_at=doc["created_at"],
    )
