from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.exercises import router as exercises_router
from app.api.routes.health import router as health_router
from app.config import settings


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(exercises_router)

    return application


app = create_app()
