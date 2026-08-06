"""Scheduler 24/7 — loop harian: fetch → resolve feedback → predict → store.

Dapat dijalankan sebagai proses standalone (direkomendasikan untuk deploy):
    python -m services.scheduler

Jalan sekali di startup, lalu tidur sampai jam jadwal berikutnya (16:30 WIB,
setelah pasar IDX tutup). Setiap loop model otomatis mempelajari outcome baru.

Dilengkapi run-lock: jika cycle sebelumnya masih jalan, cycle baru di-skip.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from datetime import time as dtime
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.database import Base, async_session_factory, engine
from app.models import Prediction, UserWatchlist
from services.data_engine import fetch_historical
from services.feedback import resolve_pending
from services.forecast import predict_all
from services.news_processor import ingest_news

logger = logging.getLogger(__name__)

JKT = ZoneInfo("Asia/Jakarta")

# Run-lock — cegah cycle overlap
_cycle_lock = asyncio.Lock()


def parse_schedule_time(raw: str) -> dtime:
    """Parse '16:30' → time(16, 30)."""
    h, m = raw.split(":")
    return dtime(int(h), int(m))


def seconds_until(now: datetime, run_at: dtime) -> int:
    """Detik sampai run_at berikutnya (hari ini jika belum lewat, else besok)."""
    target = datetime.combine(now.date(), run_at, tzinfo=now.tzinfo)
    if now >= target:
        target += timedelta(days=1)
    return int((target - now).total_seconds())


async def _watchlist_union() -> list[str]:
    """Gabungan watchlist global + semua user. Dedupe, urutkan."""
    settings = get_settings()
    tickers = set(settings.watchlist)

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                UserWatchlist.__table__.select().with_only_columns(
                    UserWatchlist.ticker
                )
            )
        ).all()
        tickers.update(r[0].upper() for r in rows)

    return sorted(tickers)


async def run_once() -> None:
    """Satu siklus harian: fetch data → resolve prediksi lama → prediksi baru."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    watchlist = await _watchlist_union()
    logger.info("Siklus dimulai — watchlist: %s", watchlist)

    async with async_session_factory() as session:
        for ticker in watchlist:
            try:
                await fetch_historical(
                    session, ticker, period=settings.fetch_period, force_fetch=True
                )
            except Exception as exc:
                logger.warning("fetch %s gagal: %s", ticker, exc)

        for ticker in watchlist:
            try:
                await ingest_news(session, ticker, limit=settings.news_limit)
            except Exception as exc:
                logger.warning("news %s gagal: %s", ticker, exc)

        for ticker in watchlist:
            try:
                await resolve_pending(session, ticker)
            except Exception as exc:
                logger.warning("resolve %s gagal: %s", ticker, exc)

        for ticker in watchlist:
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
    """Loop tanpa henti — restart-on-error, run-lock, tunggu jadwal berikutnya."""
    settings = get_settings()
    run_at = parse_schedule_time(settings.schedule_time)

    while True:
        if _cycle_lock.locked():
            logger.warning("Cycle sebelumnya masih jalan — skip cycle ini")
        else:
            async with _cycle_lock:
                try:
                    await run_once()
                except Exception as exc:
                    logger.exception("siklus harian gagal: %s", exc)

        await asyncio.sleep(seconds_until(datetime.now(JKT), run_at))


async def main() -> None:
    """Entry point standalone."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Vates scheduler dimulai (standalone)")
    try:
        await daily_loop()
    except asyncio.CancelledError:
        logger.info("Scheduler dihentikan")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler berhenti (KeyboardInterrupt)")
