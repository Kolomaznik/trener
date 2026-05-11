"""Per-user exercise state machine — slim, intrinsic state only.

Each ``user_exercises`` document tracks one user's progression on one
exercise. It stores **only** intrinsic per-user state. Catalog data
(cadence, progression goals, family, level number, …), per-user
derived values (target_reps, target_sets, rest_seconds), and
session-derived values (best_result, recent_sets,
muscle_load_by_difficulty) are computed on demand at the endpoint that
serves them — they are no longer cached on this row.

Document shape::

    {
        "user_email":            str,
        "exercise_name":         str,
        "user_level":            "beginner" | "intermediate" | "mastery",
        "completed":             bool,
        "level_history":         [ {level, trigger, achieved_at}, ... ],
        "created_at":            datetime,
        "consecutive_successes": int,    # set lazily on first streak event
    }

Lifecycle
---------
* **Add** — user explicitly adds via ``add_user_exercise``. No auto-seed.
* **List** — ``list_user_exercises`` joins the catalog and projects the
  current tier's ``target_reps`` / ``target_sets`` and a tier→seconds
  ``rest_seconds`` so the trainee list page can render without a second
  catalog round-trip.
* **Refresh after a workout** — POST /workout-sessions calls
  ``refresh_user_exercise`` which delegates to ``_check_and_advance``.
  This evaluates the latest workout_session's ``total_reps`` against
  ``progression_goals[user_level].reps`` and updates only the streak
  fields (``consecutive_successes`` / on level-up, ``user_level``,
  ``level_history``, ``completed``).

Level-up rule
-------------
A user advances ``user_level`` only when their last
``LEVEL_UP_THRESHOLD`` consecutive sets all met ``target_reps``. Any
under-target set resets the streak to zero.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.services.fitness_math import REST_SECONDS

logger = logging.getLogger(__name__)

SCHEMA_FILTER: dict[str, Any] = {
    "level": {"$exists": True},
    "family": {"$exists": True},
}
PROGRESSION_LEVELS: tuple[str, ...] = ("beginner", "intermediate", "mastery")
PROGRESSION_STARS: dict[str, int] = {
    "beginner": 1,
    "intermediate": 2,
    "mastery": 3,
}
# Canonical ordered (catalog_family_title, achievement_key) pairs. The
# tuple order drives the order in which families are rendered in the
# Trénink věžné UI; FAMILY_KEY_MAP is derived for title→key lookups.
FAMILIES: tuple[tuple[str, str], ...] = (
    ("Kliky", "pushups"),
    ("Dřepy", "squats"),
    ("Shyby", "pullups"),
    ("Zdvihy nohou", "legraises"),
    ("Mosty", "bridges"),
    ("Kliky ve stojce", "hspu"),
)
FAMILY_KEY_MAP: dict[str, str] = dict(FAMILIES)
ACHIEVEMENT_LEVELS: tuple[int, ...] = tuple(range(1, 11))

# Number of consecutive successful sets (set total_reps >= target_reps)
# required before user_level advances by one tier.
LEVEL_UP_THRESHOLD: int = 3


class LevelUpInfo(BaseModel):
    previous_level: str
    new_level: str


class UserExerciseAlreadyExists(Exception):
    """Raised when add_user_exercise is called for a (user, exercise) that
    already has a row. The endpoint layer maps this to HTTP 409."""


def _as_int(value: Any, default: int, *, field: str) -> int:
    """Coerce ``value`` to int; on a non-None garbage value, log and fall back.

    ``None`` is treated as legitimate "missing" (silently returns ``default``),
    because some call sites use this for lazily-seeded fields like
    ``consecutive_successes``. Any other unparseable value is logged as a
    warning so data-shape drift surfaces instead of silently corrupting the
    streak machine.
    """
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning(
            "user_exercises: non-integer value for %s (got %r); falling back to %d",
            field,
            value,
            default,
        )
        return default


def _normalize_progression_level(value: Any) -> str | None:
    return value if value in PROGRESSION_LEVELS else None


def empty_achievement_cells() -> dict[str, dict[str, dict[str, Any]]]:
    """Empty stars/achieved_at matrix keyed by family_key → level → cell.

    Used both when seeding ``user_achievements`` rows and when the
    Trénink věžné endpoint needs a placeholder shape.
    """
    return {
        family_key: {str(level): {"stars": 0, "achieved_at": None} for level in ACHIEVEMENT_LEVELS}
        for family_key in FAMILY_KEY_MAP.values()
    }


def _next_progression_level(level: str) -> str | None:
    try:
        current_index = PROGRESSION_LEVELS.index(level)
    except ValueError:
        return None

    next_index = current_index + 1
    if next_index >= len(PROGRESSION_LEVELS):
        return None
    return PROGRESSION_LEVELS[next_index]


def _level_history_entry(level: str, trigger: str, when: datetime) -> dict[str, Any]:
    return {"level": level, "trigger": trigger, "achieved_at": when}


async def _record_achievement(
    *,
    db: AsyncIOMotorDatabase,
    user_email: str,
    family: str,
    level_number: int,
    completed_progression_level: str,
    now: datetime,
) -> None:
    family_key = FAMILY_KEY_MAP.get(family)
    stars = PROGRESSION_STARS.get(completed_progression_level)
    if family_key is None or stars is None:
        return

    level_key = str(level_number)
    # MongoDB rejects an update that touches both an ancestor path
    # ($setOnInsert: {cells: …}) and one of its descendants
    # ($set: cells.<family>.<level>.<field>) — even when the document
    # already exists and $setOnInsert is a no-op. So the write is
    # split: first seed the document, then set the leaf fields.
    await db["user_achievements"].update_one(
        {"user_email": user_email},
        {
            "$setOnInsert": {
                "user_email": user_email,
                "cells": empty_achievement_cells(),
                "created_at": now,
            },
            "$set": {"updated_at": now},
        },
        upsert=True,
    )
    await db["user_achievements"].update_one(
        {"user_email": user_email},
        {
            "$set": {
                f"cells.{family_key}.{level_key}.stars": stars,
                f"cells.{family_key}.{level_key}.achieved_at": now,
                "updated_at": now,
            },
        },
    )


async def add_user_exercise(
    db: AsyncIOMotorDatabase,
    user_email: str,
    exercise_name: str,
) -> dict[str, Any]:
    """Add an exercise to the user's personal list.

    Inserts a slim ``user_exercises`` row at level ``beginner`` with a
    one-entry ``level_history`` (``trigger="seed"``). Raises:

    * ``ValueError`` — exercise_name does not exist in the catalog.
    * ``UserExerciseAlreadyExists`` — the user has already added this
      exercise.
    """
    exercise_doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if exercise_doc is None:
        raise ValueError(f"exercise not found: {exercise_name}")

    existing = await db["user_exercises"].find_one(
        {"user_email": user_email, "exercise_name": exercise_name}
    )
    if existing is not None:
        raise UserExerciseAlreadyExists(exercise_name)

    now = datetime.now(UTC)
    # Note: `consecutive_successes` is intentionally absent on insert. The
    # streak machine treats missing as zero (see `_check_and_advance`), and
    # the field is set lazily on the user's first successful set.
    document: dict[str, Any] = {
        "user_email": user_email,
        "exercise_name": exercise_name,
        "user_level": "beginner",
        "completed": False,
        "level_history": [_level_history_entry("beginner", "seed", now)],
        "created_at": now,
    }
    await db["user_exercises"].insert_one(document)
    return document


async def list_user_exercises(
    db: AsyncIOMotorDatabase,
    user_email: str,
) -> list[dict[str, Any]]:
    """Return every exercise the user has added, with catalog data joined
    and the current tier's targets projected.

    Empty list when the user hasn't added anything. Catalog
    ``title``/``family``/``level`` and per-tier ``target_reps`` /
    ``target_sets`` / ``rest_seconds`` are computed at read time — they
    are not cached on the row.
    """
    pipeline = [
        {"$match": {"user_email": user_email}},
        {
            "$lookup": {
                "from": "exercises",
                "localField": "exercise_name",
                "foreignField": "name",
                "as": "_catalog",
            }
        },
        {"$unwind": {"path": "$_catalog", "preserveNullAndEmptyArrays": True}},
    ]
    rows = await db["user_exercises"].aggregate(pipeline).to_list(None)

    enriched: list[dict[str, Any]] = []
    for row in rows:
        catalog = row.pop("_catalog", None) or {}
        level = _normalize_progression_level(row.get("user_level")) or "beginner"
        progression_goals = catalog.get("progression_goals") or {}
        goal = progression_goals.get(level) or {}
        enriched.append(
            {
                **row,
                "title": catalog.get("title"),
                "family": catalog.get("family"),
                "level": catalog.get("level"),
                "target_reps": goal.get("reps"),
                "target_sets": goal.get("sets"),
                "rest_seconds": REST_SECONDS.get(level, 60),
            }
        )
    enriched.sort(key=lambda r: (r.get("family") or "", r.get("level") or 0))
    return enriched


async def _check_and_advance(
    *,
    db: AsyncIOMotorDatabase,
    user_email: str,
    exercise_name: str,
) -> LevelUpInfo | None:
    """Evaluate the latest set against the current target and update
    streak / level. ``target_reps`` is now read from the catalog rather
    than the user_exercise row (which no longer caches it).
    """
    user_exercise = await db["user_exercises"].find_one(
        {"user_email": user_email, "exercise_name": exercise_name}
    )
    if user_exercise is None or user_exercise.get("completed"):
        return None

    current_level = _normalize_progression_level(user_exercise.get("user_level"))
    if current_level is None:
        return None

    exercise_doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if exercise_doc is None:
        return None
    progression_goals = exercise_doc.get("progression_goals") or {}
    current_goal = progression_goals.get(current_level) or {}
    target_reps = current_goal.get("reps")
    if target_reps is None:
        return None

    latest_session = await db["exercise_series"].find_one(
        {"user_email": user_email, "exercise_id": exercise_name},
        sort=[("started_at", -1)],
    )
    if latest_session is None:
        return None

    latest_total_reps = _as_int(latest_session.get("total_reps"), 0, field="total_reps")
    success = latest_total_reps >= _as_int(target_reps, 0, field="target_reps")
    now = datetime.now(UTC)

    if not success:
        if (
            _as_int(user_exercise.get("consecutive_successes"), 0, field="consecutive_successes")
            != 0
        ):
            await db["user_exercises"].update_one(
                {"_id": user_exercise["_id"]},
                {"$set": {"consecutive_successes": 0}},
            )
        return None

    new_streak = (
        _as_int(user_exercise.get("consecutive_successes"), 0, field="consecutive_successes") + 1
    )
    if new_streak < LEVEL_UP_THRESHOLD:
        await db["user_exercises"].update_one(
            {"_id": user_exercise["_id"]},
            {"$set": {"consecutive_successes": new_streak}},
        )
        return None

    # Threshold reached → level up.
    await _record_achievement(
        db=db,
        user_email=user_email,
        family=exercise_doc.get("family") or "",
        level_number=_as_int(exercise_doc.get("level"), 1, field="exercises.level"),
        completed_progression_level=current_level,
        now=now,
    )

    next_progression_level = _next_progression_level(current_level)
    if next_progression_level is not None:
        await db["user_exercises"].update_one(
            {"_id": user_exercise["_id"]},
            {
                "$set": {
                    "user_level": next_progression_level,
                    "consecutive_successes": 0,
                },
                "$push": {
                    "level_history": _level_history_entry(
                        next_progression_level, "consecutive_successes", now
                    ),
                },
            },
        )
        return LevelUpInfo(previous_level=current_level, new_level=next_progression_level)

    # Mastery completed → mark this exercise done. The completion
    # timestamp lives on the last level_history entry; we no longer
    # mirror it onto a separate completed_at field.
    await db["user_exercises"].update_one(
        {"_id": user_exercise["_id"]},
        {
            "$set": {
                "completed": True,
                "consecutive_successes": 0,
            },
            "$push": {
                "level_history": _level_history_entry("completed", "consecutive_successes", now),
            },
        },
    )
    return LevelUpInfo(previous_level=current_level, new_level="completed")


async def refresh_user_exercise(
    db: AsyncIOMotorDatabase,
    user_email: str,
    exercise_name: str,
) -> LevelUpInfo | None:
    """Evaluate the latest set against the streak. Returns ``None`` when
    the user hasn't added the exercise. Used from POST /workout-sessions
    only.
    """
    return await _check_and_advance(
        db=db,
        user_email=user_email,
        exercise_name=exercise_name,
    )
