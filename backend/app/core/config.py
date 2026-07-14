from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    MONGO_URL: str
    REDIS_URL: str

    JWT_SECRET: str
    JWT_EXPIRY_HOURS: int

    class Config:
        env_file = "../.env"

settings = Settings()