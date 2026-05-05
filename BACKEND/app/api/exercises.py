from typing import Any, NamedTuple

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
from app.schemas.workout_sessions import RecentSet, UserLevelInfo
from app.services.fitness_math import compute_level
from app.services.muscle_load import calculate_muscle_load
from config import settings as app_settings

router = APIRouter(prefix="/exercises", tags=["exercises"])

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}

_optional_bearer = HTTPBearer(auto_error=False)

_REST_SECONDS: dict[str, int] = {"beginner": 90, "intermediate": 60, "mastery": 45}


class _UserContext(NamedTuple):
    """Optional authentication context resolved for a single request."""

    email: str | None
    weight_kg: float | None


async def _get_optional_user_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: Database = Depends(get_db),
) -> _UserContext:
    """Return the authenticated user's email and weight_kg (both None if unauthenticated).

    Makes at most one outbound HTTP call to Google's userinfo endpoint.
    Returns ``(None, None)`` when:
    - no Authorization header is present,
    - the token is invalid / Google rejects it.
    Returns ``(email, None)`` when the user has no profile or no weight_kg set.
    """
    if credentials is None:
        return _UserContext(email=None, weight_kg=None)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                app_settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {credentials.credentials}"},
            )
    except httpx.HTTPError:
        return _UserContext(email=None, weight_kg=None)

    if resp.status_code != 200:
        return _UserContext(email=None, weight_kg=None)

    email = resp.json().get("email")
    if not email:
        return _UserContext(email=None, weight_kg=None)

    user_doc = db["users"].find_one({"email": email})
    if user_doc is None:
        return _UserContext(email=email, weight_kg=None)

    raw = user_doc.get("weight_kg")
    weight_kg = float(raw) if raw is not None else None
    return _UserContext(email=email, weight_kg=weight_kg)


def _compute_user_level_info(
    db: Database,
    user_email: str,
    exercise_id: str,
    exercise_doc: dict[str, Any],
) -> UserLevelInfo:
    """Return the authenticated user's level info for a given exercise."""
    recent_docs = list(
        db["workout_sessions"]
        .find({"user_email": user_email, "exercise_id": exercise_id})
        .sort("started_at", -1)
        .limit(5)
    )

    progression_goals: dict[str, Any] | None = exercise_doc.get("progression_goals")
    recent_reps = [doc["total_reps"] for doc in recent_docs]
    level = compute_level(recent_reps, progression_goals)

    recent_sets = [
        RecentSet(
            total_reps=doc["total_reps"],
            started_at=doc["started_at"],
            set_number=doc["set_number"],
        )
        for doc in recent_docs
    ]

    target_reps: int | None = None
    target_sets: int | None = None
    if progression_goals:
        goal = progression_goals.get(level) or {}
        target_reps = goal.get("reps")
        target_sets = goal.get("sets")

    last_best_reps = max(recent_reps) if recent_reps else None

    return UserLevelInfo(
        level=level,
        recent_sets=recent_sets,
        target_reps=target_reps,
        target_sets=target_sets,
        last_best_reps=last_best_reps,
        rest_seconds=_REST_SECONDS.get(level, 60),
    )


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
    user_level: UserLevelInfo | None = None,
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
        user_level=user_level,
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
    user_context: _UserContext = Depends(_get_optional_user_context),
) -> ExerciseDetailResponse:
    """Return full exercise detail, including pre-computed per-difficulty muscle load
    and the authenticated user's current level info.

    The function is ``async`` because the optional authentication dependency
    ``_get_optional_user_context`` makes an outbound HTTP request to Google's
    userinfo endpoint to identify the caller.

    The ``muscle_load_by_difficulty`` field is populated only when the request
    carries a valid Google access token and the authenticated user has
    ``weight_kg`` set in their profile.  It is ``null`` otherwise.

    The ``user_level`` field is populated whenever the user is authenticated,
    even if they have no workout history.  It is ``null`` for anonymous requests.
    """
    doc = db["exercises"].find_one({"id": exercise_id, **SCHEMA_FILTER})
    if doc is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    nxt = _next_in_family(db, doc)

    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None
    user_level: UserLevelInfo | None = None

    if user_context.email is not None:
        if user_context.weight_kg is not None:
            muscle_load_by_difficulty = _compute_load_for_all_difficulties(
                doc, user_context.weight_kg
            )
        user_level = _compute_user_level_info(db, user_context.email, exercise_id, doc)

    return _doc_to_detail(doc, nxt, muscle_load_by_difficulty, user_level)
