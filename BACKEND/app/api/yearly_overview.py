from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.auth import GoogleUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class DailyExerciseSummary(BaseModel):
    date: date
    count: int = Field(ge=0)


class YearlyOverviewResponse(BaseModel):
    start_date: date
    end_date: date
    days: list[DailyExerciseSummary]


@router.get("/yearly-overview", response_model=YearlyOverviewResponse)
def yearly_overview(
    end_date: str | None = Query(default=None, pattern=DATE_PATTERN),
    user: GoogleUser = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> YearlyOverviewResponse:
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

    sessions = db["workout_sessions"].find(
        {
            "user_email": user.email,
            "started_at": {"$gte": start_dt, "$lte": end_dt},
        },
        {"started_at": 1},
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

    return YearlyOverviewResponse(start_date=start, end_date=end, days=days)
