from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FACT_CHECKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "fact-checker"
    environment: str = "production"
    log_level: str = "INFO"
    checklist_path: Path = Path("data/checklists.json")

    model_base_url: str = "http://model:8000/v1"
    model_id: str = "galkinv42/qwen3_5_sft_74869"
    model_api_key: SecretStr = SecretStr("local-model-token")
    model_timeout_seconds: float = Field(default=180.0, gt=0)
    model_max_tokens: int = Field(default=4096, ge=128, le=32768)
    model_max_concurrency: int = Field(default=5, ge=1, le=128)
    model_retries: int = Field(default=2, ge=0, le=10)
    model_retry_backoff_seconds: float = Field(default=1.0, ge=0, le=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
