from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from pymongo.database import Database

from app.db import get_db

router = APIRouter(prefix="/exercises", tags=["exercises"])

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}


class ExerciseListItem(BaseModel):
    id: str
    name: str
    family: str
    level: int
    description: str
    next_exercise_id: str | None = None
    next_exercise_name: str | None = None


@router.get("", response_model=list[ExerciseListItem])
def get_exercises(
    limit: int = Query(default=100, ge=1),
    skip: int = Query(default=0, ge=0),
    db: Database = Depends(get_db),
) -> list[ExerciseListItem]:
    all_docs = list(
        db["exercises"].find(SCHEMA_FILTER).sort([("family", 1), ("level", 1)])
    )

    by_family: dict[str, list[dict[str, Any]]] = {}
    for doc in all_docs:
        by_family.setdefault(doc["family"], []).append(doc)
    for siblings in by_family.values():
        siblings.sort(key=lambda d: d["level"])

    next_by_id: dict[str, dict[str, Any]] = {}
    for siblings in by_family.values():
        for index, current in enumerate(siblings):
            if index + 1 < len(siblings):
                next_by_id[current["id"]] = siblings[index + 1]

    paginated = all_docs[skip : skip + limit]
    return [
        ExerciseListItem(
            id=doc["id"],
            name=doc["name"],
            family=doc["family"],
            level=doc["level"],
            description=doc.get("description", ""),
            next_exercise_id=next_by_id[doc["id"]]["id"] if doc["id"] in next_by_id else None,
            next_exercise_name=next_by_id[doc["id"]]["name"] if doc["id"] in next_by_id else None,
        )
        for doc in paginated
    ]
