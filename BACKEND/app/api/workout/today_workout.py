from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import GoogleUser, get_current_user
from app.sql_db import get_pool

router = APIRouter(prefix="/workout", tags=["workout"])


class WorkoutTodayItem(BaseModel):
    """One exercise in today's workout prescription."""

    name: str
    title: str
    english_name: str | None = None
    description: str
    goal: dict[str, Any]
    muscle_engagement: dict[str, Any]
    media: list[str]


@router.put("", response_model=list[WorkoutTodayItem])
async def today_workout(
    user: GoogleUser = Depends(get_current_user),
) -> list[WorkoutTodayItem]:
    """Return (and create if missing) today's workout prescription.

    First call for the user today: INSERT one ``workout`` row with
    ``plan`` populated in the same statement from the user's active
    ``exercises`` rows. Subsequent calls: ``ON CONFLICT DO NOTHING``
    swallows the insert, the existing ``plan`` stays put.

    Both statements share one connection so they run in a single
    implicit transaction; a concurrent PUT either races on the INSERT
    (only one wins) or sees the fully populated ``plan``.
    """
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 1. Upsert today's workout. The plan is computed atomically
            # from the user's currently-active exercises; ON CONFLICT
            # DO NOTHING leaves an existing row untouched.
            await cur.execute(
                """
                INSERT INTO workout (user_email, day, plan)
                SELECT %s, CURRENT_DATE,
                       COALESCE(
                         (SELECT jsonb_agg(exercise_name)
                            FROM exercises
                           WHERE user_email = %s AND completed_at IS NULL),
                         '[]'::jsonb
                       )
                ON CONFLICT (user_email, day) DO NOTHING
                """,
                (user.email, user.email),
            )

            # 2. Return the prescribed exercises with full catalog detail.
            # LATERAL jsonb_array_elements_text unpacks the JSONB array
            # into rows we can JOIN against catalog.
            await cur.execute(
                """
                SELECT c.name,
                       c.title,
                       c.english_name,
                       c.description,
                       c.goal,
                       c.muscle_engagement,
                       (SELECT COALESCE(array_agg(m.name ORDER BY m.name), ARRAY[]::text[])
                          FROM catalog_media m
                         WHERE m.exercise_name = c.name) AS media
                  FROM workout w
                  CROSS JOIN LATERAL jsonb_array_elements_text(w.plan) AS plan_name
                  JOIN catalog c ON c.name = plan_name
                 WHERE w.user_email = %s AND w.day = CURRENT_DATE
                 ORDER BY c.title COLLATE "cs-x-icu"
                """,
                (user.email,),
            )
            rows = await cur.fetchall()

    return [WorkoutTodayItem(**row) for row in rows]
