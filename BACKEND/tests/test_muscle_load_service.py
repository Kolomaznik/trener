"""Tests for the muscle_load calculation service."""

import pytest

from app.schemas.exercises import MuscleEngagement
from app.services.muscle_load import _physiological_coefficient, calculate_muscle_load

# ── _physiological_coefficient ────────────────────────────────────────────────


def test_c_phys_young_male():
    assert _physiological_coefficient(25, "M") == pytest.approx(1.0)


def test_c_phys_young_female():
    assert _physiological_coefficient(25, "F") == pytest.approx(1.1)


def test_c_phys_male_boundary_ages():
    assert _physiological_coefficient(30, "M") == pytest.approx(1.0)
    assert _physiological_coefficient(31, "M") == pytest.approx(1.05)
    assert _physiological_coefficient(40, "M") == pytest.approx(1.05)
    assert _physiological_coefficient(41, "M") == pytest.approx(1.10)
    assert _physiological_coefficient(50, "M") == pytest.approx(1.10)
    assert _physiological_coefficient(51, "M") == pytest.approx(1.15)
    assert _physiological_coefficient(60, "M") == pytest.approx(1.15)
    assert _physiological_coefficient(61, "M") == pytest.approx(1.20)


def test_c_phys_female_older():
    assert _physiological_coefficient(55, "F") == pytest.approx(1.25)


def test_c_phys_case_insensitive():
    assert _physiological_coefficient(25, "m") == _physiological_coefficient(25, "M")
    assert _physiological_coefficient(25, "f") == _physiological_coefficient(25, "F")


# ── calculate_muscle_load ─────────────────────────────────────────────────────


def test_basic_calculation():
    """Verify the formula with known values.

    h   = (175/100) * 0.40 = 0.70 m
    W   = 80 * 9.81 * 0.70 * 10 * 0.64 = 3513.408 J
    C_phys = 1.0 (male, age 25)
    L_total = 3513.408 J
    chest (40 %) → round(3513.408 * 0.40) = 1405
    """
    result = calculate_muscle_load(
        weight_kg=80,
        height_cm=175,
        age=25,
        gender="M",
        total_reps=10,
        level_coefficient=0.64,
        height_multiplier=0.40,
        muscle_engagement_percent={"chest": 40, "triceps": 30},
    )

    assert isinstance(result["chest"], MuscleEngagement)
    assert result["chest"].percent == 40
    assert result["chest"].muscle_load == round(80 * 9.81 * 0.70 * 10 * 0.64 * 1.0 * 0.40)
    assert result["triceps"].muscle_load == round(80 * 9.81 * 0.70 * 10 * 0.64 * 1.0 * 0.30)


def test_female_user_has_higher_load():
    common = dict(
        weight_kg=70,
        height_cm=165,
        age=28,
        total_reps=15,
        level_coefficient=0.35,
        height_multiplier=0.40,
        muscle_engagement_percent={"chest": 100},
    )
    male_load = calculate_muscle_load(**common, gender="M")["chest"].muscle_load
    female_load = calculate_muscle_load(**common, gender="F")["chest"].muscle_load
    assert female_load > male_load


def test_older_user_has_higher_load():
    common = dict(
        weight_kg=80,
        height_cm=175,
        total_reps=10,
        gender="M",
        level_coefficient=0.64,
        height_multiplier=0.40,
        muscle_engagement_percent={"chest": 100},
    )
    young = calculate_muscle_load(**common, age=25)["chest"].muscle_load
    old = calculate_muscle_load(**common, age=65)["chest"].muscle_load
    assert old > young


def test_empty_engagement_returns_empty():
    result = calculate_muscle_load(
        weight_kg=80,
        height_cm=175,
        age=25,
        gender="M",
        total_reps=10,
        level_coefficient=0.64,
        height_multiplier=0.40,
        muscle_engagement_percent={},
    )
    assert result == {}


def test_percent_preserved_in_result():
    result = calculate_muscle_load(
        weight_kg=80,
        height_cm=175,
        age=25,
        gender="M",
        total_reps=10,
        level_coefficient=0.64,
        height_multiplier=0.40,
        muscle_engagement_percent={"chest": 40, "triceps": 30, "deltoids": 15},
    )
    assert result["chest"].percent == 40
    assert result["triceps"].percent == 30
    assert result["deltoids"].percent == 15


def test_more_reps_means_more_load():
    common = dict(
        weight_kg=80,
        height_cm=175,
        age=25,
        gender="M",
        level_coefficient=0.64,
        height_multiplier=0.40,
        muscle_engagement_percent={"chest": 100},
    )
    low = calculate_muscle_load(**common, total_reps=5)["chest"].muscle_load
    high = calculate_muscle_load(**common, total_reps=20)["chest"].muscle_load
    assert high == 4 * low
