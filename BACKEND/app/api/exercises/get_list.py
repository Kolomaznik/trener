from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.db import SCHEMA_FILTER, get_db

router = APIRouter(prefix="/exercises", tags=["exercises"])


class CatalogExerciseItem(BaseModel):
    """Lean catalog row used by the admin Exercises Catalog table."""

    name: str
    title: str
    family: str
    level: int


@router.get("/catalog", response_model=list[CatalogExerciseItem])
async def get_exercises_catalog(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[CatalogExerciseItem]:
    """Lean read-only catalog of every exercise in the system.

    Used by the admin "Cviky (katalog)" UI. No auth required, returns
    only the four columns the table needs.
    """
    docs = await (
        db["exercises"]
        .find(SCHEMA_FILTER, {"name": 1, "title": 1, "family": 1, "level": 1, "_id": 0})
        .sort([("family", 1), ("level", 1)])
        .to_list(None)
    )
    return [CatalogExerciseItem(**doc) for doc in docs]
