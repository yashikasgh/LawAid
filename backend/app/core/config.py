from pathlib import Path
from typing import Literal

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
    AUTH_COOKIE_NAME: str = "lawaid_token"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
    )

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str | None = None

    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str | None = None

    model_config = SettingsConfigDict(env_file=REPOSITORY_ROOT / ".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
