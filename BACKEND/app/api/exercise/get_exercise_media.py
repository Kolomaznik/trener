from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import GoogleUser, get_current_user
from app.sql_db import fetchone

router = APIRouter(prefix="/exercise", tags=["exercise"])


class WorkoutMediaResponse(BaseModel):
    """One media row from the ``media`` table -- the inline ``data:`` URI
    is shipped verbatim so the frontend can drop it straight into
    ``<img src={data} />``."""

    exercise_name: str
    name: str
    data: str


@router.get(
    "/{exercise_name}/media/{media_name}",
    response_model=WorkoutMediaResponse,
)
async def get_media(
    exercise_name: str,
    media_name: str,
    user: GoogleUser = Depends(get_current_user),
) -> WorkoutMediaResponse:
    """Return one media item for one exercise.

    The workout list endpoint ships only the media names; this endpoint
    is hit once per image the UI actually needs to render, so the heavy
    base64 blobs travel one at a time.
    """
    row = await fetchone(
        "SELECT exercise_name, name, data FROM catalog_media "
        "WHERE exercise_name = %s AND name = %s",
        (exercise_name, media_name),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media {media_name!r} for exercise {exercise_name!r} not found.",
        )
    return WorkoutMediaResponse(**row)
