from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or backend/.env."""

    database_url: str = "postgres://postgres:postgres@localhost:5432/talentflow_ai"
    app_env: str = "development"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    upload_root: Path = BACKEND_DIR / "uploads"
    max_resume_size_bytes: int = 10 * 1024 * 1024
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_max_retries: int = 3
    celery_retry_backoff_seconds: int = 5

    # Authentication
    session_secret: SecretStr = SecretStr("dev-only-insecure-session-secret-change-me")
    session_cookie_name: str = "tf_session"
    session_max_age_seconds: int = 7 * 24 * 60 * 60
    session_cookie_secure: bool = False
    admin_email: str | None = None
    admin_password: SecretStr | None = None

    # Demo mode: one-click demo login, nightly data reset, and the demo banner.
    demo_mode: bool = True
    demo_recruiter_email: str = "demo@northstar.example.com"
    demo_recruiter_password: SecretStr = SecretStr("demo-recruiter")
    demo_reset_hour_utc: int = 3

    # Abuse and cost protection (counters live in Redis).
    redis_url: str = "redis://localhost:6379/2"
    ai_daily_call_limit: int = 200
    application_rate_limit_per_hour: int = 3
    login_rate_limit_per_window: int = 10
    login_rate_limit_window_seconds: int = 300
    comparison_cache_seconds: int = 24 * 60 * 60
    resume_text_max_chars: int = 20_000
    ai_max_output_tokens: int = 6_000

    # The GraphQL IDE defaults to on in development and off in production.
    graphql_ide_enabled: bool | None = None

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


    @property
    def is_production(self) -> bool:
        return self.app_env.strip().casefold() == "production"

    @property
    def graphql_ide(self) -> bool:
        if self.graphql_ide_enabled is not None:
            return self.graphql_ide_enabled
        return not self.is_production


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
