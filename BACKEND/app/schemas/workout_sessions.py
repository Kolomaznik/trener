"""Pydantic schemas for workout session documents and API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class WorkoutEvent(BaseModel):
    value: int
    token: str
    timestamp_ms: int
    timestamp_iso: str


class WorkoutSessionCreate(BaseModel):
    exercise_id: str
    exercise_name: str
    started_at: datetime
    ended_at: datetime
    total_duration_sec: float = Field(ge=0)
    total_reps: int = Field(ge=0)
    events: list[WorkoutEvent] = Field(default_factory=list)
    set_number: int = Field(ge=1)


class WorkoutSessionResponse(BaseModel):
    id: str
    user_email: str
    exercise_id: str
    exercise_name: str
    started_at: datetime
    ended_at: datetime
    total_duration_sec: float
    total_reps: int
    events: list[WorkoutEvent]
    set_number: int
    user_weight_kg: float | None = None
    user_height_cm: int | None = None
    muscle_engagement_percent: dict[str, int] = Field(default_factory=dict)
    saved_at: datetime


class RecentSet(BaseModel):
    total_reps: int
    started_at: datetime
    set_number: int


class UserLevelInfo(BaseModel):
    level: str
    recent_sets: list[RecentSet]
    target_reps: int | None = None
    target_sets: int | None = None
    last_best_reps: int | None = None
    rest_seconds: int
