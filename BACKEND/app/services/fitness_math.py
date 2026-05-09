"""Physical-condition mathematics module.

All numerical / algorithmic calculations related to fitness and physical
condition live here so that API handlers stay free of business logic and
other modules can import a single, well-tested source of truth.

Exported symbols
----------------
REST_SECONDS              : dict[str, int]
    Recommended rest period (seconds) between sets for each training level.

compute_level             : (list[int], dict | None) -> str
    Derive a user's training level from recent repetition history.

calculate_muscle_load     : (...) -> dict[str, MuscleEngagement]
    Compute per-muscle volume load (kg) for a given workout.

interpolate_missing_reps  : (list[dict], int | None) -> tuple[list[dict], int]
    Fill gaps caused by unrecognised speech in a voice-counted rep sequence.

evaluate_set_performance  : (list[dict], float | None, int | None) -> SetEvaluation | None
    Analyse pace and trend of a set and return a coaching recommendation.
"""

from datetime import UTC, datetime
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


# ---------------------------------------------------------------------------
# Rep interpolation
# ---------------------------------------------------------------------------


class SetEvaluation(BaseModel):
    """Coaching evaluation of a single set."""

    pace_label: str  # "too_fast" | "on_track" | "too_slow"
    trend_label: str  # "speeding_up" | "steady" | "slowing_down"
    # "too_few" when total_reps < target_reps, "completed" when
    # total_reps >= target_reps. ``None`` when target_reps is unknown.
    repetition_label: str | None = None
    avg_interval_sec: float
    recommendation: str
    # True iff the user reached their target rep count AND held the prescribed
    # cadence (pace_label == "on_track").  Used by the frontend to render a
    # single green "Hotovo" badge with no other tags.
    is_completed: bool = False


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


# Tuning constants for interpolation and evaluation
_DEDUP_WINDOW_MS: int = (
    1500  # same-value events within this window are deduplicated, keeping the last occurrence
)
_DEFAULT_INTERVAL_MS: float = 3000.0  # assumed rep interval when there is no history
_GAP_THRESHOLD_FACTOR: float = (
    0.5  # gaps >= 50 % of the expected duration for missing reps trigger interpolation
)
_PACE_TOO_FAST: float = 0.8  # avg < cadence × this → too fast (±20 % band)
_PACE_TOO_SLOW: float = 1.2  # avg > cadence × this → too slow
_TREND_SLOWING: float = 1.15  # second-half avg > first-half × this → slowing down
_TREND_SPEEDING: float = 0.85  # second-half avg < first-half × this → speeding up
_TARGET_INCREMENT: int = 2  # reps added to target when recommending more volume


def interpolate_missing_reps(
    counting: list[dict],
    session_start_ms: int | None = None,
) -> tuple[list[dict], int]:
    """Fill gaps caused by unrecognised speech in a voice-counted rep sequence.

    The algorithm:

    1. Sort counting events by ``timestamp_ms`` and de-duplicate
       consecutive entries with the same value within a 1 500 ms window
       (keeping the last one, matching the frontend ``shouldAcceptEvent``
       behaviour).
    2. Compute the median inter-rep interval from the de-duplicated sequence.
    3. For each consecutive pair ``(a, b)`` where ``b.value > a.value + 1``:
       if the time gap is at least 50 % of what the missing reps would need
       (very generous margin), synthesise the missing numbers with evenly
       distributed timestamps and mark them ``interpolated=True``.
    4. If the first recognised number is ``> 1`` and ``session_start_ms`` is
       known, apply the same gap check before the first event.
    5. Never synthesise reps **after** the last recognised number – the
       canonical rep count equals the last recognised value.

    Args:
        counting: Raw counting-event dicts from the workout session (as
            sent by the frontend).  Each dict must have ``value`` (int)
            and ``timestamp_ms`` (int) keys.
        session_start_ms: Unix epoch milliseconds for the session start.
            Used only to evaluate whether reps before the first recognised
            number are plausible.

    Returns:
        A ``(corrected_counting, total_reps)`` tuple where ``corrected_counting``
        is the merged list (original entries with ``interpolated=False`` and
        synthesised entries with ``interpolated=True``) sorted by timestamp,
        and ``total_reps`` is the last recognised value.
    """
    if not counting:
        return [], 0

    # Sort by timestamp and de-duplicate same-value consecutive events
    sorted_events = sorted(counting, key=lambda e: e["timestamp_ms"])
    deduped: list[dict] = []
    for ev in sorted_events:
        if (
            deduped
            and deduped[-1]["value"] == ev["value"]
            and ev["timestamp_ms"] - deduped[-1]["timestamp_ms"] <= _DEDUP_WINDOW_MS
        ):
            deduped[-1] = ev  # keep the later occurrence
        else:
            deduped.append(ev)

    if not deduped:
        return [], 0

    # Compute median inter-rep interval (ms)
    intervals_ms = [
        deduped[i + 1]["timestamp_ms"] - deduped[i]["timestamp_ms"] for i in range(len(deduped) - 1)
    ]
    median_ms: float = _median(intervals_ms) if intervals_ms else _DEFAULT_INTERVAL_MS

    def _make_synthetic(value: int, timestamp_ms: int) -> dict:
        return {
            "value": value,
            "token": str(value),
            "timestamp_ms": timestamp_ms,
            "timestamp_iso": datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat(),
            "interpolated": True,
        }

    result: list[dict] = []

    # Check for missing reps before the first event
    first = deduped[0]
    missing_before = first["value"] - 1
    if missing_before > 0 and session_start_ms is not None:
        available_ms = first["timestamp_ms"] - session_start_ms
        if available_ms >= missing_before * median_ms * _GAP_THRESHOLD_FACTOR:
            step = available_ms / (missing_before + 1)
            for i, num in enumerate(range(1, first["value"]), start=1):
                result.append(_make_synthetic(num, session_start_ms + int(step * i)))

    # Walk through the de-duplicated sequence
    for idx, ev in enumerate(deduped):
        real_ev = dict(ev)
        real_ev["interpolated"] = False
        result.append(real_ev)

        if idx < len(deduped) - 1:
            nxt = deduped[idx + 1]
            missing = nxt["value"] - ev["value"] - 1
            if missing > 0:
                gap_ms = nxt["timestamp_ms"] - ev["timestamp_ms"]
                if gap_ms >= missing * median_ms * _GAP_THRESHOLD_FACTOR:
                    step = gap_ms / (missing + 1)
                    for j, num in enumerate(range(ev["value"] + 1, nxt["value"]), start=1):
                        result.append(_make_synthetic(num, ev["timestamp_ms"] + int(step * j)))

    result.sort(key=lambda e: e["timestamp_ms"])
    total_reps = deduped[-1]["value"]
    return result, total_reps


# ---------------------------------------------------------------------------
# Set performance evaluation
# ---------------------------------------------------------------------------


def evaluate_set_performance(
    counting: list[dict],
    cadence_total_rep_time_sec: float | None,
    target_reps: int | None = None,
    total_reps: int | None = None,
) -> "SetEvaluation | None":
    """Analyse pace and trend of a set and return a coaching recommendation.

    Uses only **real** (non-interpolated) counting entries so that
    artificially inserted timestamps do not skew the averages.

    Args:
        counting: Corrected counting-event list (may include interpolated
            entries; the evaluator filters them out).
        cadence_total_rep_time_sec: Expected seconds per rep from the exercise
            cadence document.  ``None`` when cadence is not defined – in that
            case the function returns ``None``.
        target_reps: Optional target rep count used to personalise the
            recommendation when pace and trend are both good and to decide
            ``is_completed`` / ``repetition_label``.
        total_reps: Final corrected rep count for the set (post-interpolation).
            When provided together with ``target_reps``, drives the
            ``is_completed`` flag and the ``repetition_label`` on the result.

    Returns:
        A ``SetEvaluation`` instance, or ``None`` when there is not enough
        data to draw conclusions.
    """
    if cadence_total_rep_time_sec is None:
        return None

    real_events = [e for e in counting if not e.get("interpolated")]
    real_events.sort(key=lambda e: e["timestamp_ms"])

    if len(real_events) < 2:
        return None

    intervals_ms = [
        real_events[i + 1]["timestamp_ms"] - real_events[i]["timestamp_ms"]
        for i in range(len(real_events) - 1)
    ]

    avg_interval_sec = (sum(intervals_ms) / len(intervals_ms)) / 1000
    expected = cadence_total_rep_time_sec

    # Pace classification (±20 % tolerance)
    if avg_interval_sec < expected * _PACE_TOO_FAST:
        pace_label = "too_fast"
    elif avg_interval_sec > expected * _PACE_TOO_SLOW:
        pace_label = "too_slow"
    else:
        pace_label = "on_track"

    # Trend: compare first-half vs second-half average interval
    if len(intervals_ms) >= 4:
        mid = len(intervals_ms) // 2
        first_avg = sum(intervals_ms[:mid]) / mid
        second_avg = sum(intervals_ms[mid:]) / (len(intervals_ms) - mid)
        if second_avg > first_avg * _TREND_SLOWING:
            trend_label = "slowing_down"
        elif second_avg < first_avg * _TREND_SPEEDING:
            trend_label = "speeding_up"
        else:
            trend_label = "steady"
    else:
        trend_label = "steady"

    # Coaching recommendation
    cadence_str = f"{cadence_total_rep_time_sec:.0f}s/rep"
    if pace_label == "too_fast" and trend_label == "slowing_down":
        recommendation = (
            f"Začínáš příliš rychle a ke konci zpomaluješ. "
            f"Zkus udržet rovnoměrné tempo {cadence_str}."
        )
    elif pace_label == "too_fast":
        recommendation = f"Tempo je příliš rychlé. Zpomal na {cadence_str} a soustřeď se na formu."
    elif pace_label == "too_slow" and trend_label == "speeding_up":
        recommendation = "Dobře, ke konci série zrychlíš! Příště zkus začít v lepším tempu."
    elif pace_label == "too_slow":
        recommendation = f"Tempo je pomalé. Zkus zrychlit na {cadence_str}."
    elif trend_label == "slowing_down":
        recommendation = "Tempo je dobré, ale ke konci zpomaluješ. Příště zkus udržet rytmus déle."
    elif trend_label == "speeding_up":
        recommendation = "Výborně! Zrychlení v průběhu série je skvělý znak síly."
    else:
        next_target = (target_reps + _TARGET_INCREMENT) if target_reps else None
        if next_target:
            recommendation = f"Skvělé a rovnoměrné tempo! Příště zkus {next_target} opakování."
        else:
            recommendation = "Skvělé a rovnoměrné tempo! Příště přidej pár opakování."

    if target_reps is None or total_reps is None:
        repetition_label: str | None = None
    elif total_reps >= target_reps:
        repetition_label = "completed"
    else:
        repetition_label = "too_few"

    is_completed = repetition_label == "completed" and pace_label == "on_track"

    return SetEvaluation(
        pace_label=pace_label,
        trend_label=trend_label,
        repetition_label=repetition_label,
        avg_interval_sec=round(avg_interval_sec, 2),
        recommendation=recommendation,
        is_completed=is_completed,
    )
