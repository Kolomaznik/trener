from calendar import monthrange
from datetime import date, datetime
from random import randint

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
MONTH_PATTERN = r"^\d{4}-\d{2}$"


class DailyExerciseSummary(BaseModel):
    date: date
    count: int = Field(ge=0, le=12)


class MonthlyOverviewResponse(BaseModel):
    month: str = Field(pattern=MONTH_PATTERN)
    days: list[DailyExerciseSummary]


@router.get("/monthly-overview", response_model=MonthlyOverviewResponse)
def monthly_overview(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
) -> MonthlyOverviewResponse:
    if month is None:
        today = date.today()
        year = today.year
        month_index = today.month
        normalized_month = f"{year:04d}-{month_index:02d}"
    else:
        try:
            parsed = datetime.strptime(month, "%Y-%m")
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail="Parametr month musí být ve formátu YYYY-MM.",
            ) from error
        year = parsed.year
        month_index = parsed.month
        normalized_month = month

    _, days_in_month = monthrange(year, month_index)
    generated_days = [
        DailyExerciseSummary(date=date(year, month_index, day_index), count=randint(0, 12))
        for day_index in range(1, days_in_month + 1)
    ]
    return MonthlyOverviewResponse(month=normalized_month, days=generated_days)
