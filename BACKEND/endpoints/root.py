from fastapi import APIRouter
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

router = APIRouter()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "trener-backend"


class RootResponse(BaseModel):
    app: str


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(app=Settings().app_name)
