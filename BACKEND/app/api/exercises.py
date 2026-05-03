from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.db import get_db
from app.schemas.exercises import (
    Cadence,
    ExerciseDetailResponse,
    ExerciseListItem,
    Media,
    MuscleLoadRequest,
    MuscleLoadResponse,
    ProgressionGoals,
)
from app.services.muscle_load import calculate_muscle_load

router = APIRouter(prefix="/exercises", tags=["exercises"])

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}


def _next_in_family(db: Database, doc: dict[str, Any]) -> dict[str, Any] | None:
    return db["exercises"].find_one({"family": doc["family"], "level": doc["level"] + 1})


def _doc_to_detail(doc: dict[str, Any], nxt: dict[str, Any] | None) -> ExerciseDetailResponse:
    media_doc = doc.get("media") if isinstance(doc.get("media"), dict) else None
    cadence_doc = doc.get("cadence") if isinstance(doc.get("cadence"), dict) else None
    progression_doc = (
        doc.get("progression_goals") if isinstance(doc.get("progression_goals"), dict) else None
    )
    return ExerciseDetailResponse(
        id=doc["id"],
        name=doc["name"],
        english_name=doc.get("english_name"),
        family=doc["family"],
        level=doc["level"],
        description=doc.get("description", ""),
        instructions=list(doc.get("instructions", [])),
        media=Media(**media_doc) if media_doc else None,
        cadence=Cadence(**cadence_doc) if cadence_doc else None,
        progression_goals=ProgressionGoals(**progression_doc) if progression_doc else None,
        muscle_engagement_percent=dict(doc.get("muscle_engagement_percent", {})),
        level_coefficient=doc.get("level_coefficient", 0.5),
        height_multiplier=doc.get("height_multiplier", 0.5),
        next_exercise_id=nxt["id"] if nxt else None,
        next_exercise_name=nxt["name"] if nxt else None,
    )


@router.get("", response_model=list[ExerciseListItem])
def list_exercises(db: Database = Depends(get_db)) -> list[ExerciseListItem]:
    docs = list(db["exercises"].find(SCHEMA_FILTER).sort([("family", 1), ("level", 1)]))

    by_family: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        by_family.setdefault(doc["family"], []).append(doc)
    for siblings in by_family.values():
        siblings.sort(key=lambda d: d["level"])

    next_by_id: dict[str, dict[str, Any]] = {}
    for siblings in by_family.values():
        for index, current in enumerate(siblings):
            if index + 1 < len(siblings):
                next_by_id[current["id"]] = siblings[index + 1]

    items: list[ExerciseListItem] = []
    for doc in docs:
        nxt = next_by_id.get(doc["id"])
        items.append(
            ExerciseListItem(
                id=doc["id"],
                name=doc["name"],
                family=doc["family"],
                level=doc["level"],
                description=doc.get("description", ""),
                next_exercise_id=nxt["id"] if nxt else None,
                next_exercise_name=nxt["name"] if nxt else None,
            )
        )
    return items


@router.get("/family/{family}", response_model=list[ExerciseDetailResponse])
def list_exercises_by_family(
    family: str,
    db: Database = Depends(get_db),
) -> list[ExerciseDetailResponse]:
    """Return all exercises in a given family, sorted by level ascending."""
    docs = list(
        db["exercises"]
        .find({"family": family, "level": {"$exists": True}})
        .sort("level", 1)
    )
    if not docs:
        raise HTTPException(status_code=404, detail="No exercises found for this family")

    next_by_id: dict[str, dict[str, Any]] = {}
    for index, doc in enumerate(docs):
        if index + 1 < len(docs):
            next_by_id[doc["id"]] = docs[index + 1]

    return [_doc_to_detail(doc, next_by_id.get(doc["id"])) for doc in docs]


@router.get("/{exercise_id}", response_model=ExerciseDetailResponse)
def get_exercise_detail(
    exercise_id: str,
    db: Database = Depends(get_db),
) -> ExerciseDetailResponse:
    doc = db["exercises"].find_one({"id": exercise_id, **SCHEMA_FILTER})
    if doc is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    nxt = _next_in_family(db, doc)
    return _doc_to_detail(doc, nxt)


@router.post("/{exercise_id}/muscle-load", response_model=MuscleLoadResponse)
def get_muscle_load(
    exercise_id: str,
    payload: MuscleLoadRequest,
    db: Database = Depends(get_db),
) -> MuscleLoadResponse:
    """Compute per-muscle absolute load (Joules) for a given workout set."""
    doc = db["exercises"].find_one({"id": exercise_id, **SCHEMA_FILTER})
    if doc is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    muscle_engagement = calculate_muscle_load(
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        age=payload.age,
        gender=payload.gender,
        total_reps=payload.total_reps,
        level_coefficient=doc.get("level_coefficient", 0.5),
        height_multiplier=doc.get("height_multiplier", 0.5),
        muscle_engagement_percent=dict(doc.get("muscle_engagement_percent", {})),
    )
    return MuscleLoadResponse(muscle_engagement=muscle_engagement)
