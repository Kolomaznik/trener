from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from endpoints.health import router as health_router
from endpoints.monthly_overview import router as monthly_overview_router
from endpoints.root import router as root_router

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
app.include_router(monthly_overview_router)


def main() -> None:
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
