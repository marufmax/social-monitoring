from enum import Enum
import json
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EnvEnum(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    STAGING = "staging"


class LogLevelEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Core Settings
    ENVIRONMENT: EnvEnum = Field(
        default=EnvEnum.DEVELOPMENT, description="Environment name"
    )
    SERVICE_VERSION: str = Field(default="1.0.0", description="SERVICE_VERSION")
    SECRET_KEY: str = Field(default="your-secret-key-here", description="Secret key")
    APP_NAME: str = "Social Media Monitor"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    TESTING: bool = Field(default=False, description="Enable testing mode")

    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"], description="Allowed CORS origins"
    )
    ALLOWED_METHODS: List[str] = Field(
        default=["GET", "POST"], description="Allowed CORS methods"
    )

    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/social_monitoring",
        description="Database URL",
    )

    # OpenTelemetry & Logging
    OTLP_ENDPOINT: str = Field(
        default="http://alloy:4317", description="OpenTelemetry OTLP endpoint"
    )
    OTLP_TIMEOUT: int = Field(default=30, description="OTLP_TIMEOUT")
    LOG_LEVEL: LogLevelEnum = Field(default=LogLevelEnum.INFO, description="LOG_LEVEL")
    LOG_PERFORMANCE_METRICS: bool = Field(
        default=False, description="LOG_PERFORMANCE_METRICS"
    )
    LOG_SECURITY_EVENTS: bool = Field(default=True, description="LOG_SECURITY_EVENTS")

    # Performance Thresholds for Logging
    SLOW_REQUEST_THRESHOLD: float = Field(
        default=1.0, description="SLOW_REQUEST_THRESHOLD"
    )  # seconds
    LARGE_REQUEST_THRESHOLD: int = Field(
        default=1048576, description="LARGE_REQUEST_THRESHOLD"
    )  # 1MB
    LARGE_RESPONSE_THRESHOLD: int = Field(
        default=1048576, description="LARGE_RESPONSE_THRESHOLD"
    )  # 1MB

    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            try:
                # Try to parse as JSON array first
                return json.loads(v)
            except json.JSONDecodeError:
                # Fall back to comma-separated string
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ALLOWED_METHODS", mode="before")
    @classmethod
    def parse_allowed_methods(cls, v):
        if isinstance(v, str):
            try:
                # Try to parse as JSON array first
                return json.loads(v)
            except json.JSONDecodeError:
                # Fall back to comma-separated string
                return [method.strip() for method in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == EnvEnum.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == EnvEnum.PRODUCTION

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == EnvEnum.STAGING

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == EnvEnum.TESTING


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()


def get_environment_config():
    """Get environment-specific configuration overrides."""
    if settings.is_production:
        return {
            "DEBUG": False,
            "LOG_LEVEL": LogLevelEnum.INFO,
            "LOG_PERFORMANCE_METRICS": False,
            "DATABASE_POOL_SIZE": 50,
            "DATABASE_MAX_OVERFLOW": 100,
            "LOG_BATCH_SIZE": 1000,
            "LOG_BATCH_TIMEOUT": 30000,
        }
    elif settings.is_staging:
        return {
            "DEBUG": False,
            "LOG_LEVEL": LogLevelEnum.DEBUG,
            "LOG_PERFORMANCE_METRICS": True,
            "DATABASE_POOL_SIZE": 30,
            "DATABASE_MAX_OVERFLOW": 50,
        }
    else:  # development
        return {
            "DEBUG": True,
            "LOG_LEVEL": LogLevelEnum.DEBUG,
            "LOG_PERFORMANCE_METRICS": True,
            "DATABASE_POOL_SIZE": 10,
            "DATABASE_MAX_OVERFLOW": 20,
            "LOG_BATCH_SIZE": 100,
            "LOG_BATCH_TIMEOUT": 5000,
        }
