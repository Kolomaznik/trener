from typing import Any, NamedTuple

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from pymongo.database import Database

from app.db import get_db
from app.services.fitness_math import compute_level
from config import settings as app_settings

router = APIRouter(prefix="/exercises", tags=["exercises"])

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}

_optional_bearer = HTTPBearer(auto_error=False)


class ExerciseListItem(BaseModel):
    name: str
    title: str
    family: str
    level: int
    user_level: str | None = None
    next_exercise_name: str | None = None
    next_exercise_title: str | None = None


class _UserEmail(NamedTuple):
    email: str | None


async def _get_optional_user_email(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> _UserEmail:
    if credentials is None:
        return _UserEmail(email=None)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                app_settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {credentials.credentials}"},
            )
    except httpx.HTTPError:
        return _UserEmail(email=None)
    if resp.status_code != 200:
        return _UserEmail(email=None)
    email = resp.json().get("email")
    return _UserEmail(email=email or None)


@router.get("", response_model=list[ExerciseListItem])
async def get_exercises(
    limit: int = Query(default=100, ge=1),
    skip: int = Query(default=0, ge=0),
    db: Database = Depends(get_db),
    user_email: _UserEmail = Depends(_get_optional_user_email),
) -> list[ExerciseListItem]:
    all_docs = list(db["exercises"].find(SCHEMA_FILTER).sort([("family", 1), ("level", 1)]))

    by_family: dict[str, list[dict[str, Any]]] = {}
    for doc in all_docs:
        by_family.setdefault(doc["family"], []).append(doc)
    for siblings in by_family.values():
        siblings.sort(key=lambda d: d["level"])

    next_by_name: dict[str, dict[str, Any]] = {}
    for siblings in by_family.values():
        for index, current in enumerate(siblings):
            if index + 1 < len(siblings):
                next_by_name[current["name"]] = siblings[index + 1]

    user_levels: dict[str, str] = {}
    if user_email.email:
        recent_sessions = list(
            db["workout_sessions"]
            .find({"user_email": user_email.email})
            .sort("started_at", -1)
            .limit(len(all_docs) * 5)
        )
        sessions_by_exercise: dict[str, list[int]] = {}
        for session in recent_sessions:
            ex_id = session.get("exercise_id")
            if ex_id is None:
                continue
            reps_list = sessions_by_exercise.setdefault(ex_id, [])
            if len(reps_list) < 5:
                reps_list.append(session["total_reps"])
        for doc in all_docs:
            name = doc["name"]
            recent_reps = sessions_by_exercise.get(name, [])
            user_levels[name] = compute_level(recent_reps, doc.get("progression_goals"))

    paginated = all_docs[skip : skip + limit]
    return [
        ExerciseListItem(
            name=doc["name"],
            title=doc["title"],
            family=doc["family"],
            level=doc["level"],
            user_level=user_levels.get(doc["name"]),
            next_exercise_name=next_by_name[doc["name"]]["name"]
            if doc["name"] in next_by_name
            else None,
            next_exercise_title=next_by_name[doc["name"]]["title"]
            if doc["name"] in next_by_name
            else None,
        )
        for doc in paginated
    ]
