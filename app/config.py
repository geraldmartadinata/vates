from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Vates Core"
    debug: bool = True
    log_level: str = "INFO"

    # Telegram
    telegram_bot_token: str = ""

    # OpenBB
    openbb_personal_access_token: str = ""

    # Database — pakai SQLite untuk dev, siap migrasi ke PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./data/vates.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
