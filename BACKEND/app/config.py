from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "trener-backend"
    cors_origins: list[str] = ["http://localhost:5173"]

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "trener"
    mongo_exercises_collection: str = "exercises"


settings = Settings()
