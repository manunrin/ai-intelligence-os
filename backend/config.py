"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "development"
    app_port: int = 8000
    app_debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_intelligence_os"
    database_pool_min: int = 1
    database_pool_max: int = 10

    redis_url: str = "redis://localhost:6379/0"

    qdrant_url: str = "http://localhost:6333"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "intelligence"

    litellm_gateway_url: str = "http://localhost:4000"
    litellm_api_key: str = "sk-litellm-key"

    model_config = {"env_file": ".env", "env_prefix": ""}


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
