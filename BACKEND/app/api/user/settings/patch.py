from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter(tags=["user"])


class UserSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gender: Literal["male", "female"] | None = None
    height_cm: int | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    birth_year: int | None = Field(default=None, ge=1900, le=datetime.now().year)


@router.patch("/user/settings", status_code=status.HTTP_204_NO_CONTENT)
async def patch_user_settings(
    patch: UserSettingsPatch = Body(...),
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    payload = patch.model_dump(exclude_unset=True)
    if not payload:
        doc = await db["users"].find_one({"email": user.email})
    else:
        doc = await db["users"].find_one_and_update(
            {"email": user.email},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Call GET /user/settings first.",
        )
