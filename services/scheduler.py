"""Scheduler 24/7 — loop harian: fetch → resolve feedback → predict → store.

Jalan sekali di startup, lalu tidur sampai jam jadwal berikutnya (16:30 WIB,
setelah pasar IDX tutup). Setiap loop model otomatis mempelajari outcome baru.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from app.database import Base, async_session_factory, engine
from app.models import Prediction
from services.data_engine import fetch_historical
from services.feedback import resolve_pending
from services.forecast import predict_all
from services.news_processor import ingest_news

logger = logging.getLogger(__name__)

JKT = ZoneInfo("Asia/Jakarta")
RUN_TIME = dtime(16, 30)
WATCHLIST = ["BBCA", "ASII", "TLKM", "BBRI", "UNVR"]


def seconds_until(now: datetime, run_at: dtime = RUN_TIME) -> int:
    """Detik sampai run_at berikutnya (hari ini jika belum lewat, else besok)."""
    target = datetime.combine(now.date(), run_at, tzinfo=now.tzinfo)
    if now >= target:
        target += timedelta(days=1)
    return int((target - now).total_seconds())


async def run_once() -> None:
    """Satu siklus harian: fetch data → resolve prediksi lama → prediksi baru."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        for ticker in WATCHLIST:
            try:
                await fetch_historical(session, ticker, period="2y", force_fetch=True)
            except Exception as exc:
                logger.warning("fetch %s gagal: %s", ticker, exc)

        for ticker in WATCHLIST:
            try:
                await ingest_news(session, ticker, limit=30)
            except Exception as exc:
                logger.warning("news %s gagal: %s", ticker, exc)

        for ticker in WATCHLIST:
            try:
                await resolve_pending(session, ticker)
            except Exception as exc:
                logger.warning("resolve %s gagal: %s", ticker, exc)

        for ticker in WATCHLIST:
            try:
                preds = await predict_all(session, ticker)
            except Exception as exc:
                logger.warning("predict %s gagal: %s", ticker, exc)
                continue
            for p in preds:
                session.add(
                    Prediction(
                        ticker=ticker,
                        horizon_days=p["horizon"],
                        predicted_prob=p["prob_up"],
                        predicted_label=p["label"],
                        model_version=p["model_version"],
                    )
                )
            await session.commit()
            logger.info("prediksi %s tersimpan: %s", ticker, preds)


async def daily_loop() -> None:
    """Loop tanpa henti — restart-on-error, tunggu jadwal berikutnya."""
    while True:
        try:
            await run_once()
        except Exception as exc:
            logger.exception("siklus harian gagal: %s", exc)

        await asyncio.sleep(seconds_until(datetime.now(JKT)))
