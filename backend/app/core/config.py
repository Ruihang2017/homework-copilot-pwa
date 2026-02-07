from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = (
        "postgresql+asyncpg://homework_user:homework_pass@localhost:5432/homework_copilot"
    )

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # OpenAI
    openai_api_key: str = ""
    # openai_model: str = "gpt-5-mini"
    # openai_model: str = "gpt-4o"  # Balanced cost and reasoning with vision support
    openai_model: str = "gpt-5.2"  # Balanced cost and reasoning with vision support

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # URLs
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # Upload settings
    upload_dir: str = "uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
