from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument
from pymongo.database import Database

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter()


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    email: str
    gender: Literal["male", "female"] | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    birth_year: int | None = None
    created_at: datetime


class UserSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gender: Literal["male", "female"] | None = None
    height_cm: int | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    birth_year: int | None = Field(default=None, ge=1900, le=datetime.now().year)


def _to_response(doc: dict[str, Any]) -> UserSettingsResponse:
    doc.pop("_id", None)
    return UserSettingsResponse.model_validate(doc)


@router.get("/user/settings", response_model=UserSettingsResponse)
def user_settings(
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
    return _to_response(doc)


@router.patch("/user/settings", response_model=UserSettingsResponse)
def update_user_settings(
    patch: UserSettingsPatch = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> UserSettingsResponse:
    payload = patch.model_dump(exclude_unset=True)
    if not payload:
        doc = db["users"].find_one({"email": user.email})
    else:
        doc = db["users"].find_one_and_update(
            {"email": user.email},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Call GET /user/settings first.",
        )
    return _to_response(doc)
