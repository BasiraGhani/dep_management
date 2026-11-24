from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


def is_placeholder(value: str) -> bool:
    """True for the "change-me" example values in the .env.example files."""
    return "change-me" in value.lower()


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
    # Signs JWTs (HS256). PyJWT recommends at least 32 bytes for HS256 keys.
    secret_key: str = Field(min_length=32)
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

    @field_validator("cors_origins")
    @classmethod
    def no_wildcard_origin(cls, value: list[str]) -> list[str]:
        """NFR-1: CORS is limited to the frontend's origin(s), never "*"."""
        if "*" in value:
            raise ValueError("CORS_ORIGINS must list the frontend origin(s), not '*'")
        return value

    @field_validator("secret_key")
    @classmethod
    def not_a_placeholder(cls, value: str) -> str:
        """Refuse the example value from .env.example: it isn't secret."""
        if is_placeholder(value):
            raise ValueError("SECRET_KEY is still the example value; generate a real one")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
