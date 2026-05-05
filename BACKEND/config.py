from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "trener-backend"
    cors_origins: list[str] = ["http://localhost:5173"]
    cors_origin_regex: str | None = None
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "trener"
    google_userinfo_url: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    muscle_map_json_path: Path = (
        Path(__file__).resolve().parents[1] / "FRONTEND" / "src" / "assets" / "muscle-map.json"
    )

    @field_validator("google_userinfo_url", "mongo_uri", mode="before")
    @classmethod
    def strip_url_whitespace(cls, v: str) -> str:
        return v.strip()


settings = Settings()
