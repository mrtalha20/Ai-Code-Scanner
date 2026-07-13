from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "scanner"
    POSTGRES_PASSWORD: str = "scanner_dev_password"
    POSTGRES_DB: str = "scanner_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 4096

    # GitHub App
    GITHUB_APP_ID: str = ""
    GITHUB_APP_NAME: str = "ai-code-security-scanner"
    GITHUB_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Rate limiting
    RATE_LIMIT_FREE_RPM: int = 60
    RATE_LIMIT_PRO_RPM: int = 300

    # Scan limits
    MAX_CODE_SIZE_KB: int = 100
    MAX_CODE_LINES: int = 5000
    SCAN_CACHE_TTL_SECONDS: int = 86400


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
