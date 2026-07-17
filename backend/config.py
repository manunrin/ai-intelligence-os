"""Configuration management using pydantic-settings."""

from __future__ import annotations

import logging
import warnings

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # -- App --
    app_env: str = "development"
    app_port: int = 8000
    app_debug: bool = False

    # -- Database --
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_intelligence_os"
    database_pool_min: int = 1
    database_pool_max: int = 10

    # -- JWT --
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # -- Cache / Vector / Storage --
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "intelligence"

    # -- LLM Gateways --
    litellm_gateway_url: str = "http://localhost:4000"
    litellm_api_key: str = "sk-litellm-key"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    compatible_api_base: str = ""
    compatible_api_key: str = ""

    # -- Logging --
    log_level: str = "INFO"

    # -- Rate Limiting --
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 3600
    rate_limit_login_requests: int = 5
    rate_limit_login_window_seconds: int = 900

    # -- CORS --
    cors_allowed_origins: str = ""

    model_config = {"env_file": ".env", "env_prefix": "", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.app_env == "production":
            if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters in production"
                )
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
        else:
            # Development: warn but allow empty secret
            if not self.jwt_secret_key:
                warnings.warn(
                    "JWT_SECRET_KEY is empty — this is safe only in development. "
                    "Set a strong key for production.",
                    UserWarning,
                    stacklevel=2,
                )
        return self


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
