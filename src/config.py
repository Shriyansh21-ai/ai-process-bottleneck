from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    ENV: str = "dev"
    CONFIDENCE_THRESHOLD: float = 0.75

    class Config:
        env_file = ".env"

settings = Settings()
