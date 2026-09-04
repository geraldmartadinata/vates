import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from telegram.ext import Application, CommandHandler

from app.bot import error, indikator, prediksi, saham, start, watch
from app.config import get_settings
from app.database import Base, async_session_factory, engine
from app.router import router

# Bot command handlers (services layer)
from services.bot_commands import cmd_analyze, cmd_screen

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

            # Register handlers — lama
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("saham", saham))
            bot_app.add_handler(CommandHandler("indikator", indikator))
            bot_app.add_handler(CommandHandler("prediksi", prediksi))
            bot_app.add_handler(CommandHandler("watch", watch))
            # Register handlers — baru (analyzer)
            bot_app.add_handler(CommandHandler("analyze", _cmd_analyze_wrapper))
            bot_app.add_handler(CommandHandler("screen", _cmd_screen_wrapper))
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


# --- Wrapper handlers untuk inject session ---
async def _cmd_analyze_wrapper(update, context):
    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        await update.message.reply_text("Layanan belum siap. Coba lagi nanti.")
        return
    async with session_factory() as session:
        result = await cmd_analyze(
            session,
            update.message.text.split(maxsplit=1)[1]
            if len(update.message.text.split()) > 1
            else "",
        )
        if result["ok"]:
            await update.message.reply_text(result["message"], parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ {result['message']}")


async def _cmd_screen_wrapper(update, context):
    session_factory = context.bot_data.get("session_factory")
    if not session_factory:
        await update.message.reply_text("Layanan belum siap. Coba lagi nanti.")
        return
    args = update.message.text.split()[1:]
    if not args:
        await update.message.reply_text("Gunakan: /screen BBCA TLKM BBRI")
        return
    async with session_factory() as session:
        result = await cmd_screen(session, args)
        if result["ok"]:
            await update.message.reply_text(result["message"], parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ {result['message']}")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
