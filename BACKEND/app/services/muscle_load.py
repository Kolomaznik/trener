"""Muscle load calculation service.

Computes an absolute "Svalové zatížení" (Muscle Load) per muscle group
based on the user's physical profile, workout data, and exercise configuration.
"""

from app.schemas.exercises import MuscleEngagement

GRAVITY = 9.81  # m/s²


def _physiological_coefficient(age: int, gender: str) -> float:
    """Return C_phys — a heuristic scaling factor based on age and gender.

    The same mechanical work represents a higher relative load as the body
    ages (declining muscle mass / recovery capacity), so the coefficient
    increases with age.  Women typically have a lower absolute lean muscle
    mass, so a base multiplier of 1.1 is applied.

    Args:
        age: User age in years.
        gender: "M" for male, "F" for female.

    Returns:
        A float coefficient ≥ 1.0.
    """
    base = 1.0 if gender.upper() == "M" else 1.1

    if age <= 30:
        age_factor = 0.0
    elif age <= 40:
        age_factor = 0.05
    elif age <= 50:
        age_factor = 0.10
    elif age <= 60:
        age_factor = 0.15
    else:
        age_factor = 0.20

    return base + age_factor


def calculate_muscle_load(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    total_reps: int,
    level_coefficient: float,
    height_multiplier: float,
    muscle_engagement_percent: dict[str, int],
) -> dict[str, MuscleEngagement]:
    """Calculate per-muscle absolute load in Joules.

    Formulae
    --------
    h = (height_cm / 100) * height_multiplier           [m]
    W = weight_kg * g * h * total_reps * level_coefficient  [J]
    C_phys = physiological coefficient (age + gender heuristic)
    L_total = W * C_phys                                 [J]
    L_muscle = round(L_total * percent / 100)            [J]

    Args:
        weight_kg: User body weight in kilograms.
        height_cm: User height in centimetres.
        age: User age in years.
        gender: "M" or "F".
        total_reps: Number of repetitions performed.
        level_coefficient: Fraction of body weight moved (exercise difficulty).
        height_multiplier: Range of motion as a fraction of body height.
        muscle_engagement_percent: Mapping of muscle name → % engagement.

    Returns:
        Dict mapping muscle name to MuscleEngagement(percent, muscle_load).
    """
    h = (height_cm / 100.0) * height_multiplier
    w_mechanical = weight_kg * GRAVITY * h * total_reps * level_coefficient
    c_phys = _physiological_coefficient(age, gender)
    l_total = w_mechanical * c_phys

    return {
        muscle: MuscleEngagement(
            percent=pct,
            muscle_load=round(l_total * pct / 100),
        )
        for muscle, pct in muscle_engagement_percent.items()
    }
