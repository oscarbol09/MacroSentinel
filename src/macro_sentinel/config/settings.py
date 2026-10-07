"""Application settings and environment configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration for MacroSentinel."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Federal Reserve Economic Data (FRED)
    fred_api_key: Optional[str] = Field(default=None, alias="FRED_API_KEY")
    fred_base_url: str = "https://api.stlouisfed.org/fred"

    # Additional Data Sources
    bls_api_key: Optional[str] = Field(default=None, alias="BLS_API_KEY")
    cftc_app_token: Optional[str] = Field(default=None, alias="CFTC_APP_TOKEN")

    # LLM Settings
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gemini/gemini-1.5-flash", alias="LLM_MODEL")

    # Dispatchers
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")
    resend_api_key: Optional[str] = Field(default=None, alias="RESEND_API_KEY")
    alert_email_recipient: Optional[str] = Field(default=None, alias="ALERT_EMAIL_RECIPIENT")

    # Scheduler
    scan_cron_schedule: str = Field(default="0 8 * * 1-5", alias="SCAN_CRON_SCHEDULE")
    data_storage_dir: Path = Field(default=Path("./data"), alias="DATA_STORAGE_DIR")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton getter for cached configuration settings."""
    settings = Settings()
    settings.data_storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_storage_dir / "cache").mkdir(exist_ok=True)
    (settings.data_storage_dir / "reports").mkdir(exist_ok=True)
    return settings
