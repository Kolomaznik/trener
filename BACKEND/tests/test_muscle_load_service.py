"""Tests for the muscle_load calculation service."""

import pytest

from app.schemas.exercises import MuscleEngagement
from app.services.muscle_load import calculate_muscle_load

# ── calculate_muscle_load ─────────────────────────────────────────────────────


def test_basic_calculation():
    """Verify the formula: total_load = 80 * 10 * 0.64 = 512 kg.

    chest  (40 %) → round(512 * 0.40, 1) = 204.8 kg
    triceps (30 %) → round(512 * 0.30, 1) = 153.6 kg
    """
    result = calculate_muscle_load(
        weight_kg=80,
        total_reps=10,
        level_coefficient=0.64,
        muscle_engagement_percent={"chest": 40, "triceps": 30},
    )

    assert isinstance(result["chest"], MuscleEngagement)
    assert result["chest"].percent == 40
    assert result["chest"].muscle_load == pytest.approx(80 * 10 * 0.64 * 0.40, rel=1e-9)
    assert result["triceps"].muscle_load == pytest.approx(80 * 10 * 0.64 * 0.30, rel=1e-9)


def test_heavier_user_has_more_load():
    common = dict(
        total_reps=15,
        level_coefficient=0.35,
        muscle_engagement_percent={"chest": 100},
    )
    light = calculate_muscle_load(**common, weight_kg=60)["chest"].muscle_load
    heavy = calculate_muscle_load(**common, weight_kg=90)["chest"].muscle_load
    assert heavy > light
    assert heavy == pytest.approx(90 / 60 * light, rel=1e-9)


def test_higher_coefficient_means_more_load():
    common = dict(
        weight_kg=80,
        total_reps=10,
        muscle_engagement_percent={"chest": 100},
    )
    easy = calculate_muscle_load(**common, level_coefficient=0.20)["chest"].muscle_load
    hard = calculate_muscle_load(**common, level_coefficient=0.80)["chest"].muscle_load
    assert hard == pytest.approx(4 * easy, rel=1e-9)


def test_more_reps_means_more_load():
    common = dict(
        weight_kg=80,
        level_coefficient=0.64,
        muscle_engagement_percent={"chest": 100},
    )
    low = calculate_muscle_load(**common, total_reps=5)["chest"].muscle_load
    high = calculate_muscle_load(**common, total_reps=20)["chest"].muscle_load
    assert high == pytest.approx(4 * low, rel=1e-9)


def test_empty_engagement_returns_empty():
    result = calculate_muscle_load(
        weight_kg=80,
        total_reps=10,
        level_coefficient=0.64,
        muscle_engagement_percent={},
    )
    assert result == {}


def test_percent_preserved_in_result():
    result = calculate_muscle_load(
        weight_kg=80,
        total_reps=10,
        level_coefficient=0.64,
        muscle_engagement_percent={"chest": 40, "triceps": 30, "deltoids": 15},
    )
    assert result["chest"].percent == 40
    assert result["triceps"].percent == 30
    assert result["deltoids"].percent == 15


def test_muscle_load_is_float():
    result = calculate_muscle_load(
        weight_kg=80,
        total_reps=10,
        level_coefficient=0.20,
        muscle_engagement_percent={"chest": 40},
    )
    # 80 * 10 * 0.20 * 0.40 = 64.0 — should be a float
    assert isinstance(result["chest"].muscle_load, float)
    assert result["chest"].muscle_load == pytest.approx(64.0)

