import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = "Personal AI Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change-this-insecure-key-for-local-development-only-min-32-chars"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def assemble_debug(cls, v: Union[bool, str]) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in ("true", "1", "t", "yes", "y", "debug"):
                return True
            if clean in ("false", "0", "f", "no", "n", "release", "prod", "production"):
                return False
        return bool(v)

    # Server Configuration
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "personal_ai_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, values) -> str:
        if v and v.strip():
            return v.strip()
        # Default fallback constructed from individual fields
        data = values.data
        user = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "postgres")
        host = data.get("POSTGRES_HOST", "localhost")
        port = data.get("POSTGRES_PORT", 5432)
        db = data.get("POSTGRES_DB", "personal_ai_db")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: str | None, values) -> str:
        if v and v.strip():
            return v.strip()
        data = values.data
        host = data.get("REDIS_HOST", "localhost")
        port = data.get("REDIS_PORT", 6379)
        password = data.get("REDIS_PASSWORD")
        db = data.get("REDIS_DB", 0)
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{host}:{port}/{db}"

    # Celery Configuration
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v: str | None, values) -> str:
        if v and v.strip():
            return v.strip()
        return values.data.get("REDIS_URL", "redis://localhost:6379/0")

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v: str | None, values) -> str:
        if v and v.strip():
            return v.strip()
        return values.data.get("REDIS_URL", "redis://localhost:6379/0")

    # Semantic Memory & Embedding Configuration
    DEFAULT_EMBEDDING_PROVIDER: str = "local"  # "local" or "openrouter"
    DEFAULT_EMBEDDING_MODEL: str = "semantic-hash-384"
    EMBEDDING_DIMENSION: int = 384
    MEMORY_RETRIEVAL_LIMIT: int = 5
    MEMORY_SIMILARITY_THRESHOLD: float = 0.4
    MEMORY_EXTRACTION_ENABLED: bool = True

    # Sanitized representation for logging
    @property
    def sanitized_database_url(self) -> str:
        if not self.DATABASE_URL:
            return ""
        # Strip credentials for safe logging
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.DATABASE_URL)
            sanitized = parsed._replace(netloc=f"***:***@{parsed.hostname}:{parsed.port}")
            return sanitized.geturl()
        except Exception:
            return "postgresql://***:***@host:port/db"


settings = Settings()
