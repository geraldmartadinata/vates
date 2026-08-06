import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from telegram.ext import Application, CommandHandler

from app.bot import error, indikator, prediksi, saham, start, watch
from app.config import get_settings
from app.database import Base, async_session_factory, engine
from app.router import router

logger = logging.getLogger(__name__)

_bot_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: DB tables + Telegram Polling. Shutdown: cleanup.

    NOTE: Scheduler TIDAK dijalankan di sini — jalan sebagai proses
    standalone (`python -m services.scheduler`) agar API restart tidak
    mematikan pipeline harian.
    """
    settings = get_settings()

    # Init DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Init bot (hanya jika token dikonfigurasi)
    if settings.telegram_bot_token:
        try:
            bot_app = Application.builder().token(settings.telegram_bot_token).build()

            # Inject session factory ke bot_data agar handler bisa akses DB
            bot_app.bot_data["session_factory"] = async_session_factory

            # Register handlers
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("saham", saham))
            bot_app.add_handler(CommandHandler("indikator", indikator))
            bot_app.add_handler(CommandHandler("prediksi", prediksi))
            bot_app.add_handler(CommandHandler("watch", watch))
            bot_app.add_error_handler(error)

            # PTB v20+: initialize → updater.start_polling → start
            await bot_app.initialize()
            await bot_app.updater.start_polling()
            await bot_app.start()

            global _bot_app
            _bot_app = bot_app

            logger.info("Telegram bot polling started")
        except Exception as e:
            logger.exception("Failed to start Telegram bot: %s", e)
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")

    yield

    # Shutdown
    if _bot_app:
        try:
            await _bot_app.updater.stop()
            await _bot_app.stop()
        except Exception:
            pass
        logger.info("Telegram bot stopped")
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
