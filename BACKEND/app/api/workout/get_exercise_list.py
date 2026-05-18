from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import GoogleUser, get_current_user
from app.sql_db import fetchall

router = APIRouter(prefix="/workout", tags=["workout"])


class WorkoutExerciseItem(BaseModel):
    """One row of the user's active (not-yet-completed) workout list.

    Joins the user's ``exercises`` row with the corresponding ``catalog``
    entry so the frontend has everything it needs to render the workout
    card without a second round-trip.
    """

    name: str
    title: str
    english_name: str | None = None
    description: str
    goal: dict[str, Any]
    muscle_engagement: dict[str, Any]
    media: list[str]
    added_at: datetime


@router.get("", response_model=list[WorkoutExerciseItem])
async def get_exercise_list(
    user: GoogleUser = Depends(get_current_user),
) -> list[WorkoutExerciseItem]:
    """Active workout list: every exercise the user added that isn't completed yet.

    Sorted oldest-first by when the user added it, so the workout flow
    keeps a stable order across reloads.
    """
    rows = await fetchall(
        """
        SELECT c.name,
               c.title,
               c.english_name,
               c.description,
               c.goal,
               c.muscle_engagement,
               e.created_at AS added_at,
               (SELECT COALESCE(array_agg(m.name ORDER BY m.name), ARRAY[]::text[])
                  FROM media m
                 WHERE m.exercise_name = c.name) AS media
          FROM exercises e
          JOIN catalog c ON c.name = e.exercise_name
         WHERE e.user_email = %s
           AND NOT e.completed
         ORDER BY e.created_at
        """,
        (user.email,),
    )
    return [WorkoutExerciseItem(**row) for row in rows]
