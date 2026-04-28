from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class MuscleLoad(BaseModel):
    name: str
    intensity: int = Field(ge=1, le=5)


class Tempo(BaseModel):
    eccentric_seconds: int | None = None
    pause_bottom_seconds: int | None = None
    concentric_seconds: int | None = None
    pause_top_seconds: int | None = None
    raw: str


class Media(BaseModel):
    images: list[str] = Field(default_factory=list)
    video_url: str | None = None


class Progression(BaseModel):
    previous_slug: str | None = None
    next_slug: str | None = None
    unlock_condition: str | None = None


class ExerciseMetadata(BaseModel):
    source_book: str
    category: str
    level: int = Field(ge=1)
    order: int = Field(ge=1)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExerciseDocument(BaseModel):
    mongo_id: str = Field(alias="_id")
    slug: str
    name: str
    description: str
    muscle_load: list[MuscleLoad] = Field(default_factory=list)
    performance_criteria: dict[str, str] = Field(default_factory=dict)
    timing: Tempo
    steps: list[str] = Field(default_factory=list)
    media: Media = Field(default_factory=Media)
    progression: Progression = Field(default_factory=Progression)
    metadata: ExerciseMetadata


class ExerciseListItem(BaseModel):
    slug: str
    name: str
    category: str
    level: int
    muscle_load: list[MuscleLoad]
    short_description: str
    has_video: bool


class ExerciseDetail(BaseModel):
    slug: str
    name: str
    description: str
    muscle_load: list[MuscleLoad]
    performance_criteria: dict[str, str]
    timing: Tempo
    steps: list[str]
    media: Media
    progression: Progression
    metadata: ExerciseMetadata


class ExerciseListResponse(BaseModel):
    items: list[ExerciseListItem]


class ErrorResponse(BaseModel):
    detail: str


ChainMode = Literal["linear"]
