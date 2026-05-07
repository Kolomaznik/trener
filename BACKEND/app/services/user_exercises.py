from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.fitness_math import REST_SECONDS, calculate_muscle_load, compute_level

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


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
    for tier in ("beginner", "intermediate", "mastery"):
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
    next_doc = await db["exercises"].find_one(
        {"family": exercise_doc["family"], "level": exercise_doc["level"] + 1, **SCHEMA_FILTER}
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
    recent_reps = [d["total_reps"] for d in recent_docs]
    level = compute_level(recent_reps, progression_goals)
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
) -> None:
    exercise_doc = await db["exercises"].find_one({"name": exercise_name, **SCHEMA_FILTER})
    if exercise_doc is None:
        return
    await _upsert_user_exercise(
        db=db,
        user_email=user_email,
        exercise_doc=exercise_doc,
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
        {"family": exercise_doc["family"], "level": exercise_doc["level"] + 1, **SCHEMA_FILTER}
    )
    now = datetime.now(UTC)
    await db["user_exercises"].update_many(
        {"exercise_name": exercise_name},
        {"$set": {**_build_static_payload(exercise_doc, next_doc), "updated_at": now}},
    )
