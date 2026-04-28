from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_exercise_repository
from app.repositories.exercises import ExerciseRepository
from app.schemas.exercises import ErrorResponse, ExerciseDetail, ExerciseListResponse

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("", response_model=ExerciseListResponse)
def list_exercises(
    repository: Annotated[ExerciseRepository, Depends(get_exercise_repository)],
) -> ExerciseListResponse:
    return ExerciseListResponse(items=repository.list_active())


@router.get("/{slug}", response_model=ExerciseDetail, responses={404: {"model": ErrorResponse}})
def get_exercise_detail(
    slug: str,
    repository: Annotated[ExerciseRepository, Depends(get_exercise_repository)],
) -> ExerciseDetail:
    detail = repository.get_active_by_slug(slug)
    if detail is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return detail
