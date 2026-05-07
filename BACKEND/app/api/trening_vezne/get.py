from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from pymongo import ReturnDocument

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter(tags=["trening-vezne"])

FAMILIES: list[dict[str, str]] = [
    {"key": "pushups", "title": "Kliky"},
    {"key": "squats", "title": "Dřepy"},
    {"key": "pullups", "title": "Shyby"},
    {"key": "legraises", "title": "Zdvihy nohou"},
    {"key": "bridges", "title": "Mosty"},
    {"key": "hspu", "title": "Kliky ve stojce"},
]
LEVELS: list[int] = list(range(1, 11))


class FamilyMeta(BaseModel):
    key: str
    title: str


class Cell(BaseModel):
    stars: int = 0
    achieved_at: datetime | None = None


class TreningVezneResponse(BaseModel):
    families: list[FamilyMeta]
    levels: list[int]
    cells: dict[str, dict[str, Cell]]


def _empty_matrix() -> dict[str, dict[str, dict]]:
    return {
        family["key"]: {str(level): {"stars": 0, "achieved_at": None} for level in LEVELS}
        for family in FAMILIES
    }


@router.get("/trening-vezne", response_model=TreningVezneResponse)
async def get_trening_vezne(
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TreningVezneResponse:
    now = datetime.now(UTC)
    doc = await db["user_achievements"].find_one_and_update(
        {"user_email": user.email},
        {
            "$setOnInsert": {
                "user_email": user.email,
                "cells": _empty_matrix(),
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    stored_cells: dict = doc.get("cells") or {}
    reconciled: dict[str, dict[str, Cell]] = {}
    for family in FAMILIES:
        family_cells = stored_cells.get(family["key"]) or {}
        reconciled[family["key"]] = {
            str(level): Cell(**(family_cells.get(str(level)) or {})) for level in LEVELS
        }

    return TreningVezneResponse(
        families=[FamilyMeta(**f) for f in FAMILIES],
        levels=LEVELS,
        cells=reconciled,
    )
