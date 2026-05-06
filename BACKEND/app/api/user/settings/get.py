from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from pymongo import ReturnDocument
from pymongo.database import Database

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter(tags=["user"])


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    email: str
    gender: Literal["male", "female"] | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    birth_year: int | None = None
    created_at: datetime


@router.get("/user/settings", response_model=UserSettingsResponse)
def get_user_settings(
    user: GoogleUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> UserSettingsResponse:
    now = datetime.now(UTC)
    google_profile = user.model_dump(mode="json")
    doc = db["users"].find_one_and_update(
        {"email": user.email},
        {
            "$setOnInsert": {
                "created_at": now,
                "gender": None,
                "height_cm": None,
                "weight_kg": None,
                "birth_year": None,
            },
            "$set": google_profile,
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    doc.pop("_id", None)
    return UserSettingsResponse.model_validate(doc)
