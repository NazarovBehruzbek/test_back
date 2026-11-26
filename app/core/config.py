from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    APP_NAME: str = "AqlliOlam VMS"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "Asia/Tashkent"

    DATABASE_URL: PostgresDsn
    DB_ECHO: bool = False

    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=(".env", str(_BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("TIMEZONE")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Ensure the configured timezone name is valid IANA time zone."""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Noto'g'ri TIMEZONE qiymati: {value}") from exc
        return value

    @property
    def database_url_str(self) -> str:
        """Return database URL as a plain string for SQLAlchemy."""
        return str(self.DATABASE_URL)

    @property
    def tz(self) -> ZoneInfo:
        """Return ZoneInfo object for configured local timezone."""
        return ZoneInfo(self.TIMEZONE)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
