from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL",
                                  "postgresql+psycopg2://postgres:postgres@localhost:5432/social_monitoring")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()