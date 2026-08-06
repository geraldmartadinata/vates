from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Vates Core"
    debug: bool = True
    log_level: str = "INFO"

    # Telegram
    telegram_bot_token: str = ""

    # OpenBB (tidak dipakai — yfinance tanpa API key)
    openbb_personal_access_token: str = ""

    # Database — SQLite dev, siap migrasi ke PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./data/vates.db"

    # --- Scheduler ---
    schedule_time: str = "16:30"                      # WIB, setelah IDX tutup
    scheduler_watchlist: str = (
        "BBCA,ASII,TLKM,BBRI,UNVR,"
        "BBNI,BMRI,INDF,ICBP,GOTO,"
        "ANTM,MDKA,KLBF,PTBA,ADRO"
    )

    # --- Data engine ---
    fetch_retries: int = 3
    fetch_backoff_seconds: float = 2.0
    fetch_period: str = "2y"

    # --- Feedback loop ---
    event_sentiment_threshold: float = 0.3
    min_training_samples: int = 40

    # --- News ---
    news_limit: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def watchlist(self) -> list[str]:
        """Daftar ticker default dari string CSV."""
        return [t.strip().upper() for t in self.scheduler_watchlist.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
