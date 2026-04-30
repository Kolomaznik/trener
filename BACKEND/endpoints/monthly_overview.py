from calendar import monthrange
from datetime import date, datetime
from random import randint

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DailyExerciseSummary(BaseModel):
    date: date
    count: int = Field(ge=0, le=12)


class MonthlyOverviewResponse(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    days: list[DailyExerciseSummary]


class MonthlyOverviewQuery(BaseModel):
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


@router.get("/monthly-overview", response_model=MonthlyOverviewResponse)
def monthly_overview(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
) -> MonthlyOverviewResponse:
    validated_query = MonthlyOverviewQuery(month=month)

    if validated_query.month is None:
        today = date.today()
        year = today.year
        month_index = today.month
        normalized_month = f"{year:04d}-{month_index:02d}"
    else:
        try:
            parsed = datetime.strptime(validated_query.month, "%Y-%m")
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail="Parametr month musí být ve formátu YYYY-MM.",
            ) from error
        year = parsed.year
        month_index = parsed.month
        normalized_month = validated_query.month

    _, days_in_month = monthrange(year, month_index)
    generated_days = [
        DailyExerciseSummary(date=date(year, month_index, day_index), count=randint(0, 12))
        for day_index in range(1, days_in_month + 1)
    ]
    return MonthlyOverviewResponse(month=normalized_month, days=generated_days)
