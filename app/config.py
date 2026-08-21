"""
Centralized settings. Everything here is read from environment variables —
see .env.example for the full list. Never hardcode secrets or thresholds
elsewhere in the codebase; import from here instead.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Vision + embedding provider
    vision_provider: str = "gemini"          # "gemini" or "ollama"
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Database
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/flyrank_capstone"

    # Thresholds (initial values from DESIGN.md §6, tune with eval set in Phase 4)
    low_confidence_threshold: float = 0.6
    similarity_threshold: float = 0.55

    # Batch job behavior
    vision_max_retries: int = 3
    vision_retry_backoff_seconds: float = 2.0

    # Image corpus
    image_corpus_dir: str = "./data/images"


settings = Settings()
