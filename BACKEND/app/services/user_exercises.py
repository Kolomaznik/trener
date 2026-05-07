from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.services.fitness_math import REST_SECONDS, calculate_muscle_load

BIG5_LEVEL_ONE_NAMES: tuple[str, ...] = (
    "pushups_level_1",
    "squats_level_1",
    "pullups_level_1",
    "legraises_level_1",
    "bridges_level_1",
)

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
FAMILY_KEY_MAP: dict[str, str] = {
    "Kliky": "pushups",
    "Dřepy": "squats",
    "Shyby": "pullups",
    "Zdvihy nohou": "legraises",
    "Mosty": "bridges",
    "Kliky ve stojce": "hspu",
}
ACHIEVEMENT_LEVELS: tuple[int, ...] = tuple(range(1, 11))


class LevelUpInfo(BaseModel):
    previous_level: str
    new_level: str
    exercise_unlocked: str | None = None


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_progression_level(value: Any) -> str | None:
    return value if value in PROGRESSION_LEVELS else None


def _empty_achievement_cells() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        family_key: {
            str(level): {"stars": 0, "achieved_at": None} for level in ACHIEVEMENT_LEVELS
        }
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
    await db["user_achievements"].update_one(
        {"user_email": user_email},
        {
            "$setOnInsert": {
                "user_email": user_email,
                "cells": _empty_achievement_cells(),
                "created_at": now,
            },
            "$set": {
                f"cells.{family_key}.{level_key}.stars": stars,
                f"cells.{family_key}.{level_key}.achieved_at": now,
                "updated_at": now,
            },
        },
        upsert=True,
    )


def _build_static_payload(
    exercise_doc: dict[str, Any],
    next_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    media = exercise_doc.get("media")
    cadence = exercise_doc.get("cadence")
    progression_goals = exercise_doc.get("progression_goals")
    muscle_engagement_percent = exercise_doc.get("muscle_engagement_percent")
    return {
        "title": exercise_doc["title"],
        "english_name": exercise_doc.get("english_name"),
        "family": exercise_doc["family"],
        "level": exercise_doc["level"],
        "description": exercise_doc.get("description", ""),
        "media": dict(media) if isinstance(media, dict) else None,
        "cadence": dict(cadence) if isinstance(cadence, dict) else None,
        "progression_goals": dict(progression_goals) if isinstance(progression_goals, dict) else {},
        "muscle_engagement_percent": dict(muscle_engagement_percent)
        if isinstance(muscle_engagement_percent, dict)
        else {},
        "level_coefficient": exercise_doc.get("level_coefficient", 0.5),
        "height_multiplier": exercise_doc.get("height_multiplier", 0.5),
        "next_exercise_name": next_doc["name"] if next_doc else None,
        "next_exercise_title": next_doc["title"] if next_doc else None,
    }


def _compute_muscle_load_by_difficulty(
    *,
    progression_goals: dict[str, Any],
    muscle_engagement_percent: dict[str, int],
    level_coefficient: float,
    weight_kg: float | None,
) -> dict[str, dict[str, Any]] | None:
    if weight_kg is None:
        return None
    tiers: dict[str, dict[str, Any]] = {}
    for tier in PROGRESSION_LEVELS:
        goal = progression_goals.get(tier)
        if not goal:
            tiers[tier] = {}
            continue
        total_reps = _as_int(goal.get("sets"), 1) * _as_int(goal.get("reps"), 1)
        calculated = calculate_muscle_load(
            weight_kg=weight_kg,
            total_reps=total_reps,
            level_coefficient=level_coefficient,
            muscle_engagement_percent=muscle_engagement_percent,
        )
        tiers[tier] = {muscle: engagement.model_dump() for muscle, engagement in calculated.items()}
    return tiers


async def _upsert_user_exercise(
    *,
    db: AsyncIOMotorDatabase,
    user_email: str,
    exercise_doc: dict[str, Any],
    weight_kg: float | None,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    exercise_name = exercise_doc["name"]
    existing_user_exercise = await db["user_exercises"].find_one(
        {"user_email": user_email, "exercise_name": exercise_name}
    )
    next_doc = await db["exercises"].find_one(
        {"family": exercise_doc["family"], "level": exercise_doc["level"] + 1}
    )
    static_payload = _build_static_payload(exercise_doc, next_doc)
    progression_goals: dict[str, Any] = static_payload["progression_goals"]
    muscle_engagement_percent: dict[str, int] = static_payload["muscle_engagement_percent"]
    level_coefficient: float = static_payload["level_coefficient"]

    recent_docs = await (
        db["workout_sessions"]
        .find({"user_email": user_email, "exercise_id": exercise_name})
        .sort("started_at", -1)
        .limit(5)
        .to_list(None)
    )
    level = (
        _normalize_progression_level((existing_user_exercise or {}).get("user_level"))
        or "beginner"
    )
    goal = progression_goals.get(level) or {}
    best_rows = await (
        db["workout_sessions"]
        .aggregate(
            [
                {"$match": {"user_email": user_email, "exercise_id": exercise_name}},
                {"$group": {"_id": None, "best_result": {"$max": "$total_reps"}}},
            ]
        )
        .to_list(1)
    )
    best_result = best_rows[0]["best_result"] if best_rows else 0

    payload: dict[str, Any] = {
        "user_email": user_email,
        "exercise_name": exercise_name,
        **static_payload,
        "user_level": level,
        "consecutive_successes": _as_int(
            (existing_user_exercise or {}).get("consecutive_successes"),
            0,
        ),
        "completed": bool((existing_user_exercise or {}).get("completed", False)),
        "completed_at": (existing_user_exercise or {}).get("completed_at"),
        "target_reps": goal.get("reps"),
        "target_sets": goal.get("sets"),
        "best_result": best_result,
        "rest_seconds": REST_SECONDS.get(level, 60),
        "recent_sets": [
            {
                "total_reps": d["total_reps"],
                "started_at": d["started_at"],
                "set_number": d["set_number"],
            }
            for d in recent_docs
        ],
        "muscle_load_by_difficulty": _compute_muscle_load_by_difficulty(
            progression_goals=progression_goals,
            muscle_engagement_percent=muscle_engagement_percent,
            level_coefficient=level_coefficient,
            weight_kg=weight_kg,
        ),
        "updated_at": now,
    }

    await db["user_exercises"].update_one(
        {"user_email": user_email, "exercise_name": exercise_name},
        {"$setOnInsert": {"created_at": now}, "$set": payload},
        upsert=True,
    )
    return payload


async def _unlock_next_exercise(
    *,
    db: AsyncIOMotorDatabase,
    user_email: str,
    current_user_exercise: dict[str, Any],
    weight_kg: float | None,
) -> str | None:
    next_doc = await db["exercises"].find_one(
        {
            "family": current_user_exercise["family"],
            "level": current_user_exercise["level"] + 1,
        }
    )
    if next_doc is None:
        return None

    existing_next = await db["user_exercises"].find_one(
        {"user_email": user_email, "exercise_name": next_doc["name"]}
    )
    if existing_next is not None:
        return None

    await _upsert_user_exercise(
        db=db,
        user_email=user_email,
        exercise_doc=next_doc,
        weight_kg=weight_kg,
    )
    return next_doc["name"]


async def _check_and_advance(
    *,
    db: AsyncIOMotorDatabase,
    user_email: str,
    exercise_name: str,
    weight_kg: float | None,
) -> LevelUpInfo | None:
    user_exercise = await db["user_exercises"].find_one(
        {"user_email": user_email, "exercise_name": exercise_name}
    )
    if user_exercise is None or user_exercise.get("completed"):
        return None

    current_level = _normalize_progression_level(user_exercise.get("user_level"))
    target_reps = user_exercise.get("target_reps")
    recent_sets = user_exercise.get("recent_sets") or []
    if current_level is None or target_reps is None or not recent_sets:
        return None

    latest_set = recent_sets[0]
    latest_total_reps = _as_int(latest_set.get("total_reps"), 0)
    success = latest_total_reps >= _as_int(target_reps, 0)
    now = datetime.now(UTC)

    await db["user_exercises"].update_one(
        {"_id": user_exercise["_id"]},
        {"$set": {"consecutive_successes": 0, "updated_at": now}},
    )
    if not success:
        return None

    await _record_achievement(
        db=db,
        user_email=user_email,
        family=user_exercise["family"],
        level_number=_as_int(user_exercise["level"], 1),
        completed_progression_level=current_level,
        now=now,
    )

    next_progression_level = _next_progression_level(current_level)
    if next_progression_level is not None:
        next_goal = (user_exercise.get("progression_goals") or {}).get(next_progression_level) or {}
        await db["user_exercises"].update_one(
            {"_id": user_exercise["_id"]},
            {
                "$set": {
                    "user_level": next_progression_level,
                    "target_reps": next_goal.get("reps"),
                    "target_sets": next_goal.get("sets"),
                    "rest_seconds": REST_SECONDS.get(next_progression_level, 60),
                    "consecutive_successes": 0,
                    "updated_at": now,
                }
            },
        )
        return LevelUpInfo(previous_level=current_level, new_level=next_progression_level)

    unlocked_exercise = await _unlock_next_exercise(
        db=db,
        user_email=user_email,
        current_user_exercise=user_exercise,
        weight_kg=weight_kg,
    )
    await db["user_exercises"].update_one(
        {"_id": user_exercise["_id"]},
        {
            "$set": {
                "completed": True,
                "completed_at": now,
                "consecutive_successes": 0,
                "updated_at": now,
            }
        },
    )
    return LevelUpInfo(
        previous_level=current_level,
        new_level="completed",
        exercise_unlocked=unlocked_exercise,
    )


async def get_or_seed_user_exercises(
    db: AsyncIOMotorDatabase,
    user_email: str,
    weight_kg: float | None,
) -> list[dict[str, Any]]:
    existing = await (
        db["user_exercises"]
        .find({"user_email": user_email})
        .sort([("family", 1), ("level", 1)])
        .to_list(None)
    )
    if existing:
        return existing

    docs = await (
        db["exercises"]
        .find({"name": {"$in": list(BIG5_LEVEL_ONE_NAMES)}, **SCHEMA_FILTER})
        .to_list(None)
    )
    order = {name: idx for idx, name in enumerate(BIG5_LEVEL_ONE_NAMES)}
    docs.sort(key=lambda d: order.get(d["name"], 999))

    for doc in docs:
        await _upsert_user_exercise(
            db=db,
            user_email=user_email,
            exercise_doc=doc,
            weight_kg=weight_kg,
        )

    return await (
        db["user_exercises"]
        .find({"user_email": user_email})
        .sort([("family", 1), ("level", 1)])
        .to_list(None)
    )


async def refresh_user_exercise(
    db: AsyncIOMotorDatabase,
    user_email: str,
    exercise_name: str,
    weight_kg: float | None,
) -> LevelUpInfo | None:
    exercise_doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if exercise_doc is None:
        return None

    await _upsert_user_exercise(
        db=db,
        user_email=user_email,
        exercise_doc=exercise_doc,
        weight_kg=weight_kg,
    )
    return await _check_and_advance(
        db=db,
        user_email=user_email,
        exercise_name=exercise_name,
        weight_kg=weight_kg,
    )


async def sync_exercise_static_fields(
    db: AsyncIOMotorDatabase,
    exercise_name: str,
) -> None:
    exercise_doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if exercise_doc is None:
        return
    next_doc = await db["exercises"].find_one(
        {"family": exercise_doc["family"], "level": exercise_doc["level"] + 1}
    )
    now = datetime.now(UTC)
    await db["user_exercises"].update_many(
        {"exercise_name": exercise_name},
        {"$set": {**_build_static_payload(exercise_doc, next_doc), "updated_at": now}},
    )
