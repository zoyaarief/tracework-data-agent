from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Tracework API"
    environment: str = "development"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'commerce.db'}"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    max_agent_steps: int = 8
    max_query_rows: int = 200
    query_timeout_seconds: int = 8
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRACEWORK_", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
