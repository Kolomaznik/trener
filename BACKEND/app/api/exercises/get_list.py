from typing import Any, NamedTuple

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.db import get_db
from app.services.user_exercises import get_or_seed_user_exercises
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


class _UserContext(NamedTuple):
    email: str | None
    weight_kg: float | None


async def _get_optional_user_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> _UserContext:
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
    user_doc = await db["users"].find_one({"email": email}, {"weight_kg": 1})
    raw_weight_kg = user_doc.get("weight_kg") if user_doc else None
    return _UserContext(
        email=email,
        weight_kg=float(raw_weight_kg) if raw_weight_kg is not None else None,
    )


@router.get("", response_model=list[ExerciseListItem])
async def get_exercises(
    limit: int = Query(default=100, ge=1),
    skip: int = Query(default=0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user_context: _UserContext = Depends(_get_optional_user_context),
) -> list[ExerciseListItem]:
    if user_context.email:
        all_docs = await get_or_seed_user_exercises(
            db=db,
            user_email=user_context.email,
            weight_kg=user_context.weight_kg,
        )
    else:
        exercises = await (
            db["exercises"].find(SCHEMA_FILTER).sort([("family", 1), ("level", 1)]).to_list(None)
        )

        by_family: dict[str, list[dict[str, Any]]] = {}
        for doc in exercises:
            by_family.setdefault(doc["family"], []).append(doc)
        for siblings in by_family.values():
            siblings.sort(key=lambda d: d["level"])

        next_by_name: dict[str, dict[str, Any]] = {}
        for siblings in by_family.values():
            for index, current in enumerate(siblings):
                if index + 1 < len(siblings):
                    next_by_name[current["name"]] = siblings[index + 1]

        all_docs = [
            {
                **doc,
                "exercise_name": doc["name"],
                "user_level": None,
                "next_exercise_name": next_by_name[doc["name"]]["name"]
                if doc["name"] in next_by_name
                else None,
                "next_exercise_title": next_by_name[doc["name"]]["title"]
                if doc["name"] in next_by_name
                else None,
            }
            for doc in exercises
        ]

    paginated = all_docs[skip : skip + limit]
    return [
        ExerciseListItem(
            name=doc["exercise_name"],
            title=doc["title"],
            family=doc["family"],
            level=doc["level"],
            user_level=doc.get("user_level"),
            next_exercise_name=doc.get("next_exercise_name"),
            next_exercise_title=doc.get("next_exercise_title"),
        )
        for doc in paginated
    ]
