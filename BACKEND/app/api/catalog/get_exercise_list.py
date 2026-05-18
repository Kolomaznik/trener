from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import GoogleUser, get_current_user
from app.sql_db import fetchall

router = APIRouter(prefix="/catalog", tags=["catalog"])


class CatalogExerciseItem(BaseModel):
    """One row of the per-user catalog view."""

    name: str
    title: str
    status: Literal["not_added", "in_progress", "completed"]


@router.get("", response_model=list[CatalogExerciseItem])
async def get_exercise_list(
    user: GoogleUser = Depends(get_current_user),
) -> list[CatalogExerciseItem]:
    """Catalog of every exercise + the current user's per-row status.

    Status is derived from a LEFT JOIN against the user's row in
    ``exercises``: missing row -> not_added, present -> in_progress or
    completed depending on the ``completed`` flag.
    """
    rows = await fetchall(
        """
        SELECT c.name, c.title,
               CASE
                   WHEN e.exercise_name IS NULL THEN 'not_added'
                   WHEN e.completed_at IS NOT NULL THEN 'completed'
                   ELSE 'in_progress'
               END AS status
          FROM catalog c
          LEFT JOIN exercises e
            ON e.exercise_name = c.name AND e.user_email = %s
         ORDER BY c.title COLLATE "cs-x-icu"
        """,
        (user.email,),
    )
    return [CatalogExerciseItem(**row) for row in rows]
