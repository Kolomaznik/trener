"""Unit tests for the fitness_math.evaluate_set_performance ``is_completed`` flag.

The flag is True iff the user reached their target rep count *and* held the
prescribed cadence (pace_label == "on_track").  Anything else — too fast, too
slow, missing target, or missing input — must produce False.
"""

import pytest

from app.services.fitness_math import evaluate_set_performance


def _events_at_intervals(intervals_sec: list[float], start_ms: int = 1_000_000) -> list[dict]:
    """Build a synthetic event list with the given inter-rep intervals (seconds).

    The first event sits at ``start_ms``; each subsequent timestamp adds the
    matching interval.  ``value`` counts up from 1 so total reps equals
    ``len(intervals_sec) + 1``.
    """
    events = [{"value": 1, "timestamp_ms": start_ms, "interpolated": False}]
    t = start_ms
    for i, dt in enumerate(intervals_sec, start=2):
        t += int(dt * 1000)
        events.append({"value": i, "timestamp_ms": t, "interpolated": False})
    return events


class TestIsCompleted:
    """The is_completed flag combines target reached + on-track tempo."""

    def test_target_reached_and_on_track(self):
        # 6 reps at 6 s/rep — exactly the prescribed cadence.
        events = _events_at_intervals([6.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=5,
            total_reps=6,
        )
        assert result is not None
        assert result.pace_label == "on_track"
        assert result.is_completed is True

    def test_target_reached_but_too_fast(self):
        # 6 reps at 3 s/rep — way under the 6 s cadence.
        events = _events_at_intervals([3.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=5,
            total_reps=6,
        )
        assert result is not None
        assert result.pace_label == "too_fast"
        assert result.is_completed is False

    def test_target_reached_but_too_slow(self):
        # 6 reps at 10 s/rep — way over the 6 s cadence.
        events = _events_at_intervals([10.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=5,
            total_reps=6,
        )
        assert result is not None
        assert result.pace_label == "too_slow"
        assert result.is_completed is False

    def test_on_track_but_below_target(self):
        # 4 reps at 6 s/rep — perfect cadence, but target is 10.
        events = _events_at_intervals([6.0] * 3)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=10,
            total_reps=4,
        )
        assert result is not None
        assert result.pace_label == "on_track"
        assert result.is_completed is False

    def test_target_reps_missing(self):
        events = _events_at_intervals([6.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=None,
            total_reps=6,
        )
        assert result is not None
        assert result.is_completed is False

    def test_total_reps_missing(self):
        events = _events_at_intervals([6.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=5,
            total_reps=None,
        )
        assert result is not None
        assert result.is_completed is False

    def test_cadence_missing_returns_none(self):
        events = _events_at_intervals([6.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=None,
            target_reps=5,
            total_reps=6,
        )
        assert result is None

    def test_exactly_at_target_counts_as_completed(self):
        # total_reps == target_reps is the boundary; must be inclusive.
        events = _events_at_intervals([6.0] * 4)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=5,
            total_reps=5,
        )
        assert result is not None
        assert result.is_completed is True

    @pytest.mark.parametrize("over_target", [1, 5, 20])
    def test_above_target_counts_as_completed(self, over_target: int):
        events = _events_at_intervals([6.0] * 5)
        result = evaluate_set_performance(
            events,
            cadence_total_rep_time_sec=6.0,
            target_reps=5,
            total_reps=5 + over_target,
        )
        assert result is not None
        assert result.is_completed is True
