from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.sql_db import fetchone

router = APIRouter(prefix="/catalog", tags=["catalog"])


class CatalogExerciseDetail(BaseModel):
    """One catalog exercise with its full detail."""

    name: str
    title: str
    english_name: str | None = None
    description: str
    goal: dict[str, Any]
    muscle_engagement: dict[str, Any]
    media: list[str]


@router.get("/{exercise_name}", response_model=CatalogExerciseDetail)
async def get_exercise_detail(
    exercise_name: str,
) -> CatalogExerciseDetail:
    """Return one catalog exercise by name, with the list of media slots
    (just the names; fetch each blob via ``/exercise/{name}/media/{slot}``).
    """
    row = await fetchone(
        """
        SELECT c.name,
               c.title,
               c.english_name,
               c.description,
               c.goal,
               c.muscle_engagement,
               (SELECT COALESCE(array_agg(m.name ORDER BY m.name), ARRAY[]::text[])
                  FROM catalog_media m
                 WHERE m.exercise_name = c.name) AS media
          FROM catalog c
         WHERE c.name = %s
        """,
        (exercise_name,),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise {exercise_name!r} not found in catalog.",
        )
    return CatalogExerciseDetail(**row)
