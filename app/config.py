"""
Central configuration for the INGRES-AI backend.

"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App -----------------------------------------------------------
    APP_NAME: str = "INGRES-AI Backend"
    APP_ENV: str = "development"  # development | production


    GROQ_API_KEY: str = "put your appi groq key"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
 
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    LLM_TEMPERATURE: float = 0.4
    LLM_MAX_TOKENS: int = 700
    LLM_TIMEOUT_SECONDS: int = 30


    WATER_DATA_API_KEY: str = "58c991bd-cad3-44f5-a6a4-eddefa145b25"
    WATER_DATA_BASE_URL: str = "https://api.data.gov.in/resource"

    WATER_DATA_RESOURCE_ID: str = "9d2e7887-084c-458c-a6c8-29a280de2b19"
    WATER_DATA_TIMEOUT_SECONDS: int = 15

    USE_LIVE_WATER_API: bool = False

    # --- CORS ------------------------------------------------------------
    # Comma-separated list of origins allowed to call this API from a browser.
    FRONTEND_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5500,http://127.0.0.1:5500"
    )

    # --- Conversation memory (in-process, no DB) ------------------------
    MAX_HISTORY_TURNS: int = 6
    SESSION_TTL_MINUTES: int = 60

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.FRONTEND_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
