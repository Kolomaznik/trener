from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.auth import GoogleUser, get_current_user
from app.sql_db import fetchone

router = APIRouter(tags=["user"])


# Sloupce co se refreshují z Google profilu při každém přihlášení. Pořadí
# musí odpovídat VALUES (%s, ...) v INSERT_SQL níže.
_GOOGLE_FIELDS = ("sub", "name", "picture")


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    email: str
    gender: Literal["male", "female"] | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    birth_year: int | None = None
    created_at: datetime


@router.get("/user", response_model=UserSettingsResponse)
async def get_user_settings(
    user: GoogleUser = Depends(get_current_user),
) -> UserSettingsResponse:
    """Upsert the user row from the Google profile and return the full record.

    On first call for a new email the row is inserted with all custom fields
    NULL and ``created_at = now()`` (DB default). On every subsequent call
    only the Google profile columns get refreshed -- custom fields and
    ``created_at`` are untouched. Mirrors the prior Mongo
    ``$setOnInsert`` + ``$set google_profile`` upsert.
    """
    google_profile = user.model_dump(mode="json")
    params = (user.email,) + tuple(google_profile.get(field) for field in _GOOGLE_FIELDS)

    row = await fetchone(
        f"""\
            INSERT INTO users (email, {", ".join(_GOOGLE_FIELDS)})
            VALUES ({", ".join(["%s"] * (1 + len(_GOOGLE_FIELDS)))})
            ON CONFLICT (email) DO UPDATE SET
                {", ".join(f"{c} = EXCLUDED.{c}" for c in _GOOGLE_FIELDS)}
            RETURNING *
        """,
        params,
    )
    return UserSettingsResponse.model_validate(row)
