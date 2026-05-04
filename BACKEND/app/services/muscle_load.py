"""Muscle load calculation service.

Computes "Přemístěná zátěž" (Volume Load) per muscle group in kilograms —
the same metric used in strength training: how many kg of (body) weight were
effectively moved by each muscle group.
"""

from app.schemas.exercises import MuscleEngagement


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
    total_load = weight_kg × total_reps × level_coefficient   [kg]
    muscle_load = round(total_load × percent / 100, 1)        [kg]

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
