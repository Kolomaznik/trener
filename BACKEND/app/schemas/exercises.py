"""Pure-Pydantic schemas for exercise documents and API responses.

Lives in `app/schemas/` so it can be imported by other projects in this repo
(notably MONGO_DB tests) without dragging in FastAPI / pymongo / config.
"""

from pydantic import BaseModel, Field

from app.schemas.workout_sessions import UserLevelInfo


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


class MuscleEngagement(BaseModel):
    """Per-muscle engagement with computed volume load in kg."""

    percent: int
    muscle_load: float = 0.0  # "Přemístěná zátěž" in kg


class MuscleLoadByDifficulty(BaseModel):
    """Volume load (kg) per muscle for each difficulty tier.

    Computed server-side from the authenticated user's weight and
    the exercise's progression_goals.  Absent (None) when the user
    is not authenticated or has no weight recorded in their profile.
    """

    beginner: dict[str, MuscleEngagement] = Field(default_factory=dict)
    intermediate: dict[str, MuscleEngagement] = Field(default_factory=dict)
    mastery: dict[str, MuscleEngagement] = Field(default_factory=dict)


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
    # Free-form: keys are author-chosen labels (e.g. ``"img_1"``,
    # ``"youtube_tutorial"``), values are URLs or ``data:`` URIs.  The
    # frontend decides how to render each entry based on the value.
    media: dict[str, str] | None = None
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
    muscle_load_by_difficulty: MuscleLoadByDifficulty | None = None
    user_level: UserLevelInfo | None = None
