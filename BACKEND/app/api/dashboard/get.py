from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class DailyExerciseSummary(BaseModel):
    date: date
    count: int = Field(ge=0)


class YearSummary(BaseModel):
    start_date: date
    end_date: date
    days: list[DailyExerciseSummary]


class DashboardResponse(BaseModel):
    year_summary: YearSummary


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    end_date: str | None = Query(default=None, pattern=DATE_PATTERN),
    user: GoogleUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DashboardResponse:
    if end_date is None:
        end = date.today()
    else:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail="Parametr end_date musí být ve formátu YYYY-MM-DD.",
            ) from error

    end_monday = end - timedelta(days=end.weekday())
    start = end_monday - timedelta(weeks=52)

    start_dt = datetime(start.year, start.month, start.day)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, 999999)

    sessions = (
        await db["exercise_series"]
        .find(
            {
                "user_email": user.email,
                "started_at": {"$gte": start_dt, "$lte": end_dt},
            },
            {"started_at": 1},
        )
        .to_list(None)
    )

    counts: dict[date, int] = {}
    for session in sessions:
        session_date = session["started_at"].date()
        counts[session_date] = counts.get(session_date, 0) + 1

    days: list[DailyExerciseSummary] = []
    current = start
    while current <= end:
        days.append(DailyExerciseSummary(date=current, count=counts.get(current, 0)))
        current += timedelta(days=1)

    year_summary = YearSummary(start_date=start, end_date=end, days=days)

    return DashboardResponse(year_summary=year_summary)
