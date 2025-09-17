from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EnvEnum(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    APP_NAME: str = "Social Media Monitor"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    TESTING: bool = Field(default=False, description="Enable testing mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    OTLP_ENDPOINT: str = Field(
        default="http://alloy:4317", description="OpenTelemetry OTLP endpoint"
    )

    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@postgres:5432/social_monitoring",
    )

    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
