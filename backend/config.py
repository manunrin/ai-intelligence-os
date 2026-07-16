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

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Compatible (Qwen, DeepSeek, etc.)
    compatible_api_base: str = ""
    compatible_api_key: str = ""

    model_config = {"env_file": ".env", "env_prefix": "", "extra": "ignore"}


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
