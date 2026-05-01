import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "trener-backend"
    cors_origins: list[str] = ["http://localhost:5173"]
    muscle_map_json_path: Path = (
        Path(__file__).resolve().parents[1] / "FRONTEND" / "src" / "assets" / "muscle-map.json"
    )


settings = Settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"app": settings.app_name}


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

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
