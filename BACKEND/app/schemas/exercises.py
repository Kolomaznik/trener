"""Pure-Pydantic schemas for exercise documents and API responses.

Lives in `app/schemas/` so it can be imported by other projects in this repo
(notably MONGO_DB tests) without dragging in FastAPI / pymongo / config.
"""

from pydantic import BaseModel, Field


class Cadence(BaseModel):
    eccentric_sec: int
    pause_bottom_sec: int
    concentric_sec: int
    pause_top_sec: int
    total_rep_time_sec: int
    coach_note: str


class ProgressionGoal(BaseModel):
    sets: int
    reps: int


class ProgressionGoals(BaseModel):
    beginner: ProgressionGoal
    intermediate: ProgressionGoal
    mastery: ProgressionGoal
    coach_note: str


class Media(BaseModel):
    youtube_tutorial: str | None = None
    thumbnail_url: str | None = None


class MuscleEngagement(BaseModel):
    """Per-muscle engagement with optional computed absolute load."""

    percent: int
    muscle_load: int = 0


class ExerciseDocument(BaseModel):
    """Shape of a single document in the `exercises` MongoDB collection.

    Pydantic ignores unknown fields by default, so MongoDB's `_id` (and any
    other extras) are silently accepted.
    """

    id: str
    name: str
    english_name: str | None = None
    family: str
    level: int
    description: str
    instructions: list[str] = Field(default_factory=list)
    media: Media | None = None
    cadence: Cadence | None = None
    progression_goals: ProgressionGoals | None = None
    muscle_engagement_percent: dict[str, int] = Field(default_factory=dict)
    level_coefficient: float = 0.5
    height_multiplier: float = 0.5


class ExerciseListItem(BaseModel):
    id: str
    name: str
    family: str
    level: int
    description: str
    next_exercise_id: str | None = None
    next_exercise_name: str | None = None


class ExerciseDetailResponse(ExerciseDocument):
    next_exercise_id: str | None = None
    next_exercise_name: str | None = None


class MuscleLoadRequest(BaseModel):
    weight_kg: float = Field(ge=20, le=300)
    height_cm: float = Field(ge=50, le=250)
    age: int = Field(ge=5, le=120)
    gender: str = Field(pattern="^(M|F)$")
    total_reps: int = Field(ge=1)


class MuscleLoadResponse(BaseModel):
    muscle_engagement: dict[str, MuscleEngagement]
