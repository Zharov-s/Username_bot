from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    allowed_source_name: str = Field(
        default="ваш разрешённый CSV-источник с opt-in",
        alias="ALLOWED_SOURCE_NAME",
    )

    bot_rate_limit_per_minute: int = Field(default=20, alias="BOT_RATE_LIMIT_PER_MINUTE")
    max_bulk_numbers: int = Field(default=200, alias="MAX_BULK_NUMBERS")
    max_import_rows: int = Field(default=5000, alias="MAX_IMPORT_ROWS")
    max_upload_size_bytes: int = Field(default=2_000_000, alias="MAX_UPLOAD_SIZE_BYTES")
    default_region: str = Field(default="RU", alias="DEFAULT_REGION")
    privacy_contact_email: str = Field(default="privacy@example.com", alias="PRIVACY_CONTACT_EMAIL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
