import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.health import router as health_router
from app.api.root import router as root_router
from app.api.user_settings import router as user_settings_router
from app.api.yearly_overview import router as yearly_overview_router
from config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root_router)
app.include_router(health_router)
app.include_router(user_settings_router)
app.include_router(yearly_overview_router)


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


@app.get("/muscle-map/data", response_model=dict[str, MuscleMetrics])
def muscle_map_data() -> dict[str, MuscleMetrics]:
    return {muscle_id: MuscleMetrics() for muscle_id in get_muscle_ids()}


def main() -> None:
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)


if __name__ == "__main__":
    main()
