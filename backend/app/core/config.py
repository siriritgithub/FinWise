from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://finwise:finwise123@db:3306/finwise"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-32-char-random-string"
    REFRESH_SECRET_KEY: str = "change-me-refresh-secret-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OCR
    TESSERACT_CMD: str = ""          # e.g. /usr/bin/tesseract
    OCR_PROVIDER: str = "tesseract"  # "tesseract" | "google" | "mock"
    GOOGLE_VISION_API_KEY: str = ""

    # App
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10
    FRONTEND_URL: str = "http://localhost:5173"

    # Optional conversational LLMs
    # Ollama is the default because it runs locally and does not require API credits.
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Optional cloud LLM fallback
    OPENAI_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-luna"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
