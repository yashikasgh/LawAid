from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    POSTGRES_USER: str = "lawaid"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "lawaid"
    DATABASE_URL: str

    MONGO_URL: str
    REDIS_URL: str

    JWT_SECRET: str
    JWT_EXPIRY_HOURS: int

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str | None = None

    model_config = SettingsConfigDict(env_file=REPOSITORY_ROOT / ".env", extra="ignore")

settings = Settings()
