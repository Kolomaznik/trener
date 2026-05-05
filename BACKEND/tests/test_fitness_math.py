"""Tests for the fitness_math module.

All physical-condition calculations are centralised in
``app.services.fitness_math``.  This test suite covers every exported
symbol: REST_SECONDS, compute_level, and calculate_muscle_load.
"""

import pytest

from app.schemas.exercises import MuscleEngagement
from app.services.fitness_math import REST_SECONDS, calculate_muscle_load, compute_level

# ── REST_SECONDS ──────────────────────────────────────────────────────────────


class TestRestSeconds:
    def test_contains_all_levels(self):
        assert set(REST_SECONDS.keys()) == {"beginner", "intermediate", "mastery"}

    def test_beginner_rest_is_90(self):
        assert REST_SECONDS["beginner"] == 90

    def test_intermediate_rest_is_60(self):
        assert REST_SECONDS["intermediate"] == 60

    def test_mastery_rest_is_45(self):
        assert REST_SECONDS["mastery"] == 45

    def test_rest_decreases_with_level(self):
        assert REST_SECONDS["beginner"] > REST_SECONDS["intermediate"] > REST_SECONDS["mastery"]


# ── compute_level ─────────────────────────────────────────────────────────────


class TestComputeLevel:
    def test_no_history_returns_beginner(self):
        assert compute_level([], None) == "beginner"

    def test_no_history_with_goals_returns_beginner(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([], goals) == "beginner"

    def test_no_goals_returns_beginner(self):
        assert compute_level([100], None) == "beginner"

    def test_below_beginner_threshold_returns_beginner(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([5, 6, 7], goals) == "beginner"

    def test_at_beginner_threshold_returns_intermediate(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([10, 10, 10], goals) == "intermediate"

    def test_above_beginner_below_mastery_returns_intermediate(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([20, 25, 30], goals) == "intermediate"

    def test_at_mastery_threshold_returns_mastery(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([50, 50, 50], goals) == "mastery"

    def test_above_mastery_threshold_returns_mastery(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([60, 70], goals) == "mastery"

    def test_uses_average_not_latest(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        # average = (5 + 15) / 2 = 10 → intermediate
        assert compute_level([5, 15], goals) == "intermediate"

    def test_single_rep_entry(self):
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        assert compute_level([10], goals) == "intermediate"

    def test_missing_beginner_key_treats_threshold_as_zero(self):
        # beginner_reps defaults to 0 when the key is absent → any reps ≥ 0 → intermediate
        goals = {"mastery": {"reps": 50}}
        assert compute_level([1], goals) == "intermediate"

    def test_missing_mastery_key_treats_threshold_as_zero(self):
        # mastery_reps defaults to 0 → avg ≥ 0 → mastery
        goals = {"beginner": {"reps": 10}}
        assert compute_level([5], goals) == "mastery"

    def test_returns_string(self):
        result = compute_level([20], {"beginner": {"reps": 10}, "mastery": {"reps": 50}})
        assert isinstance(result, str)

    def test_level_maps_to_rest_seconds(self):
        """Every level returned by compute_level must exist in REST_SECONDS."""
        goals = {"beginner": {"reps": 10}, "mastery": {"reps": 50}}
        for reps in ([5], [15], [55]):
            level = compute_level(reps, goals)
            assert level in REST_SECONDS


# ── calculate_muscle_load ─────────────────────────────────────────────────────


class TestCalculateMuscleLoad:
    def test_basic_calculation(self):
        """Verify the formula: total_load = 80 * 10 * 0.64 = 512 kg.

        chest   (40%) → round(512 * 0.40, 1) = 204.8 kg
        triceps (30%) → round(512 * 0.30, 1) = 153.6 kg
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

    def test_heavier_user_has_more_load(self):
        common = dict(
            total_reps=15,
            level_coefficient=0.35,
            muscle_engagement_percent={"chest": 100},
        )
        light = calculate_muscle_load(**common, weight_kg=60)["chest"].muscle_load
        heavy = calculate_muscle_load(**common, weight_kg=90)["chest"].muscle_load
        assert heavy > light
        assert heavy == pytest.approx(90 / 60 * light, rel=1e-9)

    def test_higher_coefficient_means_more_load(self):
        common = dict(
            weight_kg=80,
            total_reps=10,
            muscle_engagement_percent={"chest": 100},
        )
        easy = calculate_muscle_load(**common, level_coefficient=0.20)["chest"].muscle_load
        hard = calculate_muscle_load(**common, level_coefficient=0.80)["chest"].muscle_load
        assert hard == pytest.approx(4 * easy, rel=1e-9)

    def test_more_reps_means_more_load(self):
        common = dict(
            weight_kg=80,
            level_coefficient=0.64,
            muscle_engagement_percent={"chest": 100},
        )
        low = calculate_muscle_load(**common, total_reps=5)["chest"].muscle_load
        high = calculate_muscle_load(**common, total_reps=20)["chest"].muscle_load
        assert high == pytest.approx(4 * low, rel=1e-9)

    def test_empty_engagement_returns_empty(self):
        result = calculate_muscle_load(
            weight_kg=80,
            total_reps=10,
            level_coefficient=0.64,
            muscle_engagement_percent={},
        )
        assert result == {}

    def test_percent_preserved_in_result(self):
        result = calculate_muscle_load(
            weight_kg=80,
            total_reps=10,
            level_coefficient=0.64,
            muscle_engagement_percent={"chest": 40, "triceps": 30, "deltoids": 15},
        )
        assert result["chest"].percent == 40
        assert result["triceps"].percent == 30
        assert result["deltoids"].percent == 15

    def test_muscle_load_is_float(self):
        result = calculate_muscle_load(
            weight_kg=80,
            total_reps=10,
            level_coefficient=0.20,
            muscle_engagement_percent={"chest": 40},
        )
        # 80 * 10 * 0.20 * 0.40 = 64.0
        assert isinstance(result["chest"].muscle_load, float)
        assert result["chest"].muscle_load == pytest.approx(64.0)

    def test_result_keys_match_engagement_keys(self):
        engagement = {"chest": 40, "triceps": 30, "core": 20}
        result = calculate_muscle_load(
            weight_kg=75,
            total_reps=12,
            level_coefficient=0.5,
            muscle_engagement_percent=engagement,
        )
        assert set(result.keys()) == set(engagement.keys())

    def test_zero_weight_gives_zero_load(self):
        result = calculate_muscle_load(
            weight_kg=0,
            total_reps=10,
            level_coefficient=0.64,
            muscle_engagement_percent={"chest": 100},
        )
        assert result["chest"].muscle_load == 0.0

    def test_zero_reps_gives_zero_load(self):
        result = calculate_muscle_load(
            weight_kg=80,
            total_reps=0,
            level_coefficient=0.64,
            muscle_engagement_percent={"chest": 100},
        )
        assert result["chest"].muscle_load == 0.0

    def test_load_proportional_to_engagement_percent(self):
        result = calculate_muscle_load(
            weight_kg=80,
            total_reps=10,
            level_coefficient=0.5,
            muscle_engagement_percent={"primary": 60, "secondary": 30},
        )
        # primary should be exactly twice secondary
        assert result["primary"].muscle_load == pytest.approx(2 * result["secondary"].muscle_load)
