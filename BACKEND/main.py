from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exercises import router as exercises_router
from app.api.health import router as health_router
from app.api.muscle_map import router as muscle_map_router
from app.api.root import router as root_router
from app.api.user_settings import router as user_settings_router
from app.api.workout_sessions import router as workout_sessions_router
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
app.include_router(muscle_map_router)
app.include_router(exercises_router)
app.include_router(workout_sessions_router)


def main() -> None:
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)


if __name__ == "__main__":
    main()
