from datetime import date, datetime, timedelta
from random import randint

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class DailyExerciseSummary(BaseModel):
    date: date
    count: int = Field(ge=0, le=12)


class YearlyOverviewResponse(BaseModel):
    start_date: date
    end_date: date
    days: list[DailyExerciseSummary]


@router.get("/yearly-overview", response_model=YearlyOverviewResponse)
def yearly_overview(
    end_date: str | None = Query(default=None, pattern=DATE_PATTERN),
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

    days: list[DailyExerciseSummary] = []
    current = start
    while current <= end:
        days.append(DailyExerciseSummary(date=current, count=randint(0, 12)))
        current += timedelta(days=1)

    return YearlyOverviewResponse(start_date=start, end_date=end, days=days)
