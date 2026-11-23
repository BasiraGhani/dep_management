from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings, read from environment variables and `backend/.env`.

    Environment variables take precedence over the `.env` file. Names are
    case-insensitive, so `DATABASE_URL` sets `database_url`.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./dept.db"
    secret_key: str = Field(min_length=16)
    access_token_expire_minutes: int = Field(default=60, ge=1)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    first_admin_username: str | None = None
    first_admin_password: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string, e.g. `http://a.com,http://b.com`."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
