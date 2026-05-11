import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard.get import router as dashboard_router
from app.api.dashboard.muscle_load_get import router as dashboard_muscle_load_router
from app.api.exercise_series.post import router as exercise_series_router
from app.api.exercises.get_detail import router as exercises_detail_router
from app.api.exercises.get_list import router as exercises_list_router
from app.api.health.get import router as health_router
from app.api.trening_vezne.get import router as trening_vezne_router
from app.api.user.settings.get import router as user_settings_get_router
from app.api.user.settings.patch import router as user_settings_patch_router
from app.api.user_exercises.get import router as user_exercises_get_router
from app.api.user_exercises.post import router as user_exercises_post_router
from config import settings

app = FastAPI(title=settings.app_name)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(dashboard_muscle_load_router)
app.include_router(exercises_list_router)
app.include_router(exercises_detail_router)
app.include_router(exercise_series_router)
app.include_router(user_exercises_get_router)
app.include_router(user_exercises_post_router)
app.include_router(user_settings_get_router)
app.include_router(user_settings_patch_router)
app.include_router(trening_vezne_router)


def main() -> None:
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)


if __name__ == "__main__":
    main()
