from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status
from psycopg import sql
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, ConfigDict, Field

from app.auth import GoogleUser, get_current_user
from app.sql_db import get_pool

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
    pool: AsyncConnectionPool = Depends(get_pool),
) -> None:
    payload = patch.model_dump(exclude_unset=True)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if not payload:
                await cur.execute("SELECT 1 FROM users WHERE email = %s", (user.email,))
                exists = await cur.fetchone()
            else:
                # Column names are whitelisted by Pydantic (extra="forbid") so the
                # set of payload keys is bounded; wrap them in Identifier anyway
                # so psycopg handles quoting safely.
                set_clause = sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(sql.Identifier(col)) for col in payload
                )
                stmt = sql.SQL("UPDATE users SET {} WHERE email = %s RETURNING email").format(
                    set_clause
                )
                await cur.execute(stmt, (*payload.values(), user.email))
                exists = await cur.fetchone()

    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Call GET /user/settings first.",
        )
