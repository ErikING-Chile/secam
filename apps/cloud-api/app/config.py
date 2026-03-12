"""Application configuration."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "Secam API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+psycopg://secam:password@localhost:5432/secam"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    ENCRYPTION_KEY: str = ""  # Fernet key for RTSP encryption
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    RATE_LIMIT_PER_MINUTE: int = 60

    # Storage
    STORAGE_PATH: str = "/app/storage"

    # RTSP diagnostics
    RTSP_DIAGNOSTIC_SOCKET_TIMEOUT_SECONDS: float = 3.0
    RTSP_DIAGNOSTIC_OPEN_TIMEOUT_MS: int = 3000
    RTSP_DIAGNOSTIC_READ_TIMEOUT_MS: int = 3000

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
