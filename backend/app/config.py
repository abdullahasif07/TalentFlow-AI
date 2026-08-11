from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or backend/.env."""

    database_url: str = "postgres://postgres:postgres@localhost:5432/talentflow_ai"
    app_env: str = "development"
    upload_root: Path = BACKEND_DIR / "uploads"
    max_resume_size_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "models": {
            "models": ["app.db.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": True,
    "timezone": "UTC",
}
