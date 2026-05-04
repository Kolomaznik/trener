from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from app.db import get_db
from app.schemas.exercises import (
    Cadence,
    ExerciseDetailResponse,
    ExerciseListItem,
    MuscleLoadByDifficulty,
    ProgressionGoals,
)
from app.services.muscle_load import calculate_muscle_load
from config import settings as app_settings

router = APIRouter(prefix="/exercises", tags=["exercises"])

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}

_optional_bearer = HTTPBearer(auto_error=False)


async def _get_weight_kg(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: Database = Depends(get_db),
) -> float | None:
    """Return the authenticated user's weight_kg from the database, or None.

    Returns None when:
    - no Authorization header is present,
    - the token is invalid / Google rejects it,
    - the user has no profile yet, or
    - weight_kg has not been filled in.
    """
    if credentials is None:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                app_settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {credentials.credentials}"},
            )
    except httpx.HTTPError:
        return None

    if resp.status_code != 200:
        return None

    email = resp.json().get("email")
    if not email:
        return None

    user_doc = db["users"].find_one({"email": email})
    if user_doc is None:
        return None

    raw = user_doc.get("weight_kg")
    return float(raw) if raw is not None else None


def _compute_load_for_all_difficulties(
    doc: dict[str, Any],
    weight_kg: float,
) -> MuscleLoadByDifficulty:
    """Compute volume load (kg) per muscle for each of the three difficulty tiers."""
    level_coefficient: float = doc.get("level_coefficient", 0.5)
    muscle_engagement: dict[str, int] = dict(doc.get("muscle_engagement_percent", {}))
    progression: dict[str, Any] = doc.get("progression_goals") or {}

    tiers: dict[str, dict] = {}
    for tier in ("beginner", "intermediate", "mastery"):
        goal = progression.get(tier)
        if goal and muscle_engagement:
            total_reps = int(goal.get("sets", 1)) * int(goal.get("reps", 1))
            tiers[tier] = calculate_muscle_load(
                weight_kg=weight_kg,
                total_reps=total_reps,
                level_coefficient=level_coefficient,
                muscle_engagement_percent=muscle_engagement,
            )
        else:
            tiers[tier] = {}

    return MuscleLoadByDifficulty(
        beginner=tiers["beginner"],
        intermediate=tiers["intermediate"],
        mastery=tiers["mastery"],
    )


def _next_in_family(db: Database, doc: dict[str, Any]) -> dict[str, Any] | None:
    return db["exercises"].find_one({"family": doc["family"], "level": doc["level"] + 1})


def _doc_to_detail(
    doc: dict[str, Any],
    nxt: dict[str, Any] | None,
    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None,
) -> ExerciseDetailResponse:
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
        media=dict(media_doc) if media_doc else None,
        cadence=Cadence(**cadence_doc) if cadence_doc else None,
        progression_goals=ProgressionGoals(**progression_doc) if progression_doc else None,
        muscle_engagement_percent=dict(doc.get("muscle_engagement_percent", {})),
        level_coefficient=doc.get("level_coefficient", 0.5),
        height_multiplier=doc.get("height_multiplier", 0.5),
        next_exercise_id=nxt["id"] if nxt else None,
        next_exercise_name=nxt["name"] if nxt else None,
        muscle_load_by_difficulty=muscle_load_by_difficulty,
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
        db["exercises"].find({"family": family, "level": {"$exists": True}}).sort("level", 1)
    )
    if not docs:
        raise HTTPException(status_code=404, detail="No exercises found for this family")

    next_by_id: dict[str, dict[str, Any]] = {}
    for index, doc in enumerate(docs):
        if index + 1 < len(docs):
            next_by_id[doc["id"]] = docs[index + 1]

    return [_doc_to_detail(doc, next_by_id.get(doc["id"])) for doc in docs]


@router.get("/{exercise_id}", response_model=ExerciseDetailResponse)
async def get_exercise_detail(
    exercise_id: str,
    db: Database = Depends(get_db),
    weight_kg: float | None = Depends(_get_weight_kg),
) -> ExerciseDetailResponse:
    """Return full exercise detail, including pre-computed per-difficulty muscle load.

    The function is ``async`` because the optional authentication dependency
    ``_get_weight_kg`` makes an outbound HTTP request to Google's userinfo
    endpoint to identify the caller.

    The ``muscle_load_by_difficulty`` field is populated only when the request
    carries a valid Google access token and the authenticated user has
    ``weight_kg`` set in their profile.  It is ``null`` otherwise.
    """
    doc = db["exercises"].find_one({"id": exercise_id, **SCHEMA_FILTER})
    if doc is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    nxt = _next_in_family(db, doc)

    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None
    if weight_kg is not None:
        muscle_load_by_difficulty = _compute_load_for_all_difficulties(doc, weight_kg)

    return _doc_to_detail(doc, nxt, muscle_load_by_difficulty)
