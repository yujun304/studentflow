from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://studentflow:studentflow@localhost:5432/studentflow"
    jwt_secret: str = Field(
        default="development-secret-change-before-production-1234", min_length=32
    )
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cookie_secure: bool = False
    cookie_domain: str | None = None
    frontend_origin: str = "http://localhost:5173"
    storage_root: Path = Path(".data/uploads")
    storage_backend: Literal["local", "s3"] = "local"
    max_upload_bytes: int = 20 * 1024 * 1024
    default_timezone: str = "Asia/Seoul"
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:studentflow@localhost"

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def blank_domain_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def allowed_frontend_origins(self) -> set[str]:
        return {
            origin.strip().rstrip("/")
            for origin in self.frontend_origin.split(",")
            if origin.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
