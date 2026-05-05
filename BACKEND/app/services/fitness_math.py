"""Physical-condition mathematics module.

All numerical / algorithmic calculations related to fitness and physical
condition live here so that API handlers stay free of business logic and
other modules can import a single, well-tested source of truth.

Exported symbols
----------------
REST_SECONDS          : dict[str, int]
    Recommended rest period (seconds) between sets for each training level.

compute_level         : (list[int], dict | None) -> str
    Derive a user's training level from recent repetition history.

calculate_muscle_load : (...) -> dict[str, MuscleEngagement]
    Compute per-muscle volume load (kg) for a given workout.
"""

from typing import Any

from pydantic import BaseModel


class MuscleEngagement(BaseModel):
    """Per-muscle engagement with computed volume load in kg."""

    percent: int
    muscle_load: float = 0.0

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REST_SECONDS: dict[str, int] = {
    "beginner": 90,
    "intermediate": 60,
    "mastery": 45,
}

# ---------------------------------------------------------------------------
# Level computation
# ---------------------------------------------------------------------------


def compute_level(recent_reps: list[int], progression_goals: dict[str, Any] | None) -> str:
    """Derive a user's training level from recent repetition history.

    The level is determined by comparing the *average* total_reps across the
    last N sessions against the thresholds stored in ``progression_goals``.

    Args:
        recent_reps: List of ``total_reps`` values from recent workout sessions
            (most-recent first).  An empty list means no history.
        progression_goals: Mapping with at least ``"beginner"`` and
            ``"mastery"`` keys, each containing a ``"reps"`` threshold.
            May be ``None`` when the exercise has no goals defined.

    Returns:
        One of ``"beginner"``, ``"intermediate"``, or ``"mastery"``.
    """
    if not recent_reps or not progression_goals:
        return "beginner"
    avg = sum(recent_reps) / len(recent_reps)
    mastery_reps = (progression_goals.get("mastery") or {}).get("reps", 0)
    beginner_reps = (progression_goals.get("beginner") or {}).get("reps", 0)
    if avg >= mastery_reps:
        return "mastery"
    if avg >= beginner_reps:
        return "intermediate"
    return "beginner"


# ---------------------------------------------------------------------------
# Muscle-load calculation
# ---------------------------------------------------------------------------


def calculate_muscle_load(
    *,
    weight_kg: float,
    total_reps: int,
    level_coefficient: float,
    muscle_engagement_percent: dict[str, int],
) -> dict[str, MuscleEngagement]:
    """Calculate per-muscle volume load in kilograms.

    Formula
    -------
    total_load   = weight_kg × total_reps × level_coefficient   [kg]
    muscle_load  = round(total_load × percent / 100, 1)         [kg]

    This is directly analogous to the "tonnage" concept in weight training:
    an 80 kg user doing 10 reps of a calisthenics exercise that moves 20 % of
    body weight produces a total volume of 80 × 10 × 0.20 = 160 kg.

    Args:
        weight_kg: User body weight in kilograms.
        total_reps: Total number of repetitions (sets × reps).
        level_coefficient: Fraction of body weight engaged (exercise difficulty).
        muscle_engagement_percent: Mapping of muscle name → % engagement (0–100).

    Returns:
        Dict mapping muscle name to MuscleEngagement(percent, muscle_load_kg).
    """
    total_load = weight_kg * total_reps * level_coefficient

    return {
        muscle: MuscleEngagement(
            percent=pct,
            muscle_load=round(total_load * pct / 100, 1),
        )
        for muscle, pct in muscle_engagement_percent.items()
    }
