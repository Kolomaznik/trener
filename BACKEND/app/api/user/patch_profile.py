from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field

from app.auth import GoogleUser, get_current_user
from app.sql_db import fetchone

router = APIRouter(tags=["user"])


class UserSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gender: Literal["male", "female"] | None = None
    height_cm: int | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    birth_year: int | None = Field(default=None, ge=1900, le=datetime.now().year)


@router.patch("/user", status_code=status.HTTP_204_NO_CONTENT)
async def patch_user_settings(
    patch: UserSettingsPatch = Body(...),
    user: GoogleUser = Depends(get_current_user),
) -> None:
    payload = patch.model_dump(exclude_unset=True)

    if not payload:
        exists = await fetchone("SELECT 1 FROM users WHERE email = %s", (user.email,))
    else:
        # Column names are whitelisted by Pydantic (extra="forbid") so the
        # set of payload keys is bounded; wrap them in Identifier anyway
        # so psycopg handles quoting safely.
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col)) for col in payload
        )
        stmt = sql.SQL("UPDATE users SET {} WHERE email = %s RETURNING email").format(set_clause)
        exists = await fetchone(stmt, (*payload.values(), user.email))

    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Call GET /user first.",
        )
