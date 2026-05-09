from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.services.user_exercises import list_user_exercises

router = APIRouter(prefix="/user-exercises", tags=["user-exercises"])


class UserExerciseListItem(BaseModel):
    """One entry in the user's personal exercise list.

    Only the fields the trainee Moje cviky page actually renders. Per-set
    history (recent_sets, best_result) is computed at the detail
    endpoint, not here — keeps this response lean.
    """

    exercise_name: str
    title: str | None = None
    family: str | None = None
    level: int | None = None
    user_level: str
    target_reps: int | None = None
    target_sets: int | None = None
    rest_seconds: int = 60
    consecutive_successes: int = 0
    completed: bool = False


@router.get("", response_model=list[UserExerciseListItem])
async def get_user_exercises(
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[UserExerciseListItem]:
    """Return every exercise the authenticated user has added.

    Empty list when the user hasn't added anything yet — the frontend
    shows an empty-state CTA pointing to ``/admin/exercises``.
    """
    docs: list[dict[str, Any]] = await list_user_exercises(db, user.email)
    return [UserExerciseListItem(**doc) for doc in docs]
