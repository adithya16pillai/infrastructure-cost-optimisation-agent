from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Mode
    mock_aws: bool = True

    # LLM
    anthropic_api_key: str | None = None
    validator_model: str = "claude-sonnet-4-6"

    # Storage
    database_url: str = "sqlite:///./app.db"

    # Logging
    log_level: str = "INFO"

    # AWS
    aws_region: str = "us-east-1"

    # Detector thresholds (consumed from PRD 03 onward)
    idle_cpu_percent_threshold: float = 5.0
    idle_lookback_days: int = 14
    snapshot_age_days_threshold: int = 180

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
