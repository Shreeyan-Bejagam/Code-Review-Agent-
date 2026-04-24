"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the AI code reviewer service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    github_webhook_secret: str = Field(..., min_length=1)
    github_app_id: str = Field(..., min_length=1)
    github_private_key: str = Field(..., min_length=1)
    github_api_base_url: str = "https://api.github.com"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_base_url: str = "https://api.anthropic.com"

    database_url: str = Field(..., min_length=1)
    redis_url: str = Field(..., min_length=1)
    rq_queue_name: str = "pr_reviews"

    semgrep_config: str = "auto"
    max_inline_comments: int = 20
    request_timeout_seconds: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
