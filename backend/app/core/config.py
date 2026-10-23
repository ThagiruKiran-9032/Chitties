from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Locate .env relative to this file: backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Chitties"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "1234567890"
    POSTGRES_DB: str = "chitties_db"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:1234567890@localhost:5432/chitties_db"
    TEST_DATABASE_URL: str = "postgresql+psycopg2://postgres:1234567890@localhost:5432/chitties_test_db"

    # Security & Tokens
    SECRET_KEY: str = "chitties_dev_secret_key_random_signature_2026_secured"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # SMTP Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "cluelescompany@gmail.com"
    SMTP_PASSWORD: str = "zpvtbwpgjpxefpcj"
    EMAILS_FROM_EMAIL: str = "cluelescompany@gmail.com"
    EMAILS_FROM_NAME: str = "Chitties Platform"
    SMTP_TLS: bool = True

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
