import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/muscle-map", tags=["muscle-map"])


class MuscleMetrics(BaseModel):
    strength: int = 0
    increment_since_last_exercise: int = 0


def get_muscle_ids() -> list[str]:
    try:
        data = json.loads(settings.muscle_map_json_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Muscle map file not found: {settings.muscle_map_json_path}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in muscle map file: {settings.muscle_map_json_path}",
        ) from exc

    groups = data.get("highlightableMuscleGroups", [])
    muscle_ids: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        muscle_id = group.get("id")
        if isinstance(muscle_id, str):
            muscle_ids.append(muscle_id)
    return muscle_ids


@router.get("/data", response_model=dict[str, MuscleMetrics])
def muscle_map_data() -> dict[str, MuscleMetrics]:
    return {muscle_id: MuscleMetrics() for muscle_id in get_muscle_ids()}
