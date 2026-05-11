from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from pymongo import ReturnDocument

from app.auth import GoogleUser, get_current_user
from app.db import get_db
from app.services.user_exercises import (
    ACHIEVEMENT_LEVELS,
    FAMILIES,
    empty_achievement_cells,
)

router = APIRouter(tags=["trening-vezne"])


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


_FAMILY_META: list[FamilyMeta] = [FamilyMeta(key=key, title=title) for title, key in FAMILIES]
_LEVELS: list[int] = list(ACHIEVEMENT_LEVELS)


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
                "cells": empty_achievement_cells(),
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    stored_cells: dict = doc.get("cells") or {}
    reconciled: dict[str, dict[str, Cell]] = {}
    for family in _FAMILY_META:
        family_cells = stored_cells.get(family.key) or {}
        reconciled[family.key] = {
            str(level): Cell(**(family_cells.get(str(level)) or {})) for level in _LEVELS
        }

    return TreningVezneResponse(
        families=_FAMILY_META,
        levels=_LEVELS,
        cells=reconciled,
    )
