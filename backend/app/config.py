from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    DATABASE_URL: str = os.getenv("DATABASE_URL",
                                  "postgresql+psycopg2://postgres:postgres@localhost:5432/social_monitoring")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    APP_NAME: str = "Social Media Monitor"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    TESTING: bool = Field(default=False, description="Enable testing mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")

    # Database Settings
    DATABASE_URL: str = Field(
        description="Synchronous database URL for migrations",
    )
    ASYNC_DATABASE_URL: str = Field(
        default="",
        description="Async database URL for application"
    )

    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # OpenSearch Settings
    OPENSEARCH_URL: str = Field(
        default="http://localhost:9200",
        description="OpenSearch connection URL"
    )
    OPENSEARCH_INDEX_PREFIX: str = Field(
        default="smm",
        description="Prefix for OpenSearch indices"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    class Config:
        case_sensitive = True



@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()