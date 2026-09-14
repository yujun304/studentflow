from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
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
    max_upload_bytes: int = 100 * 1024 * 1024
    default_timezone: str = "Asia/Seoul"
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:studentflow@localhost"
    proposal_ai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "PROPOSAL_AI_API_KEY"),
    )
    proposal_ai_enabled: bool = False
    proposal_ai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "PROPOSAL_AI_BASE_URL"),
    )
    proposal_ai_model: str = Field(
        default="gpt-5-mini",
        validation_alias=AliasChoices("OPENROUTER_MODEL", "PROPOSAL_AI_MODEL"),
    )
    proposal_transcription_model: str = "whisper-1"
    proposal_transcription_language: str = "ko"
    proposal_transcription_provider: Literal["local", "api"] = "local"
    proposal_local_whisper_model: str = "small"
    proposal_local_whisper_device: str = "cpu"
    proposal_local_whisper_compute_type: str = "int8"
    proposal_local_whisper_cache_dir: Path = Path(".data/whisper-models")
    proposal_local_whisper_cpu_threads: int = Field(default=4, ge=1, le=32)
    proposal_transcription_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROPOSAL_TRANSCRIPTION_API_KEY", "OPENAI_API_KEY"),
    )
    proposal_transcription_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROPOSAL_TRANSCRIPTION_BASE_URL", "OPENAI_BASE_URL"),
    )
    proposal_ai_timeout_seconds: int = Field(default=120, ge=10, le=600)
    proposal_transcript_max_chars: int = Field(default=100000, ge=1000, le=1000000)
    proposal_agenda_recommendation_threshold: int = Field(default=10, ge=1)
    proposal_required_feedback_recommendation_threshold: int = Field(default=13, ge=1)
    proposal_summary_max_items: int = Field(default=8, ge=1, le=30)
    proposal_audio_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    proposal_transcription_chunk_max_bytes: int = Field(default=24 * 1024 * 1024, ge=1)
    proposal_audio_extensions: str = "flac,mp3,mp4,mpeg,mpga,m4a,ogg,wav,webm"

    @property
    def allowed_proposal_audio_extensions(self) -> set[str]:
        return {
            value.strip().lower().lstrip(".")
            for value in self.proposal_audio_extensions.split(",")
            if value.strip()
        }

    @property
    def effective_transcription_api_key(self) -> str | None:
        return self.proposal_transcription_api_key or self.proposal_ai_api_key

    @property
    def effective_transcription_base_url(self) -> str:
        return self.proposal_transcription_base_url or self.proposal_ai_base_url

    @property
    def effective_transcription_model(self) -> str:
        model = self.proposal_transcription_model.strip()
        if "openrouter.ai" in self.effective_transcription_base_url and model == "whisper-1":
            return "openai/whisper-1"
        return model

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
