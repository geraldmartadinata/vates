"""Feedback loop — resolve prediksi setelah horizon, kategorikan miss.

Miss dipisah jadi dua jenis:
- "event": ada berita kontra-arah berdampak besar selama horizon
           (keputusan benar tapi kejadian tak terduga dari pihak ketiga).
- "model": tidak ada katalis → kesalahan fundamental/pemikiran model.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import News, Prediction
from services.cache import get_cached_prices

logger = logging.getLogger(__name__)

EVENT_SENTIMENT_THRESHOLD = 0.3


async def resolve_pending(session, ticker: str) -> int:
    """Resolve semua prediksi yang horizonnya sudah berakhir.

    Returns:
        Jumlah prediksi yang berhasil di-resolve.
    """
    now = datetime.utcnow()
    pending = (
        (
            await session.execute(
                select(Prediction).where(
                    Prediction.ticker == ticker,
                    Prediction.resolved_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    resolved = 0
    for pred in pending:
        end = pred.created_at + timedelta(days=pred.horizon_days)
        if end > now:
            continue

        actual_ret = await _actual_return(session, ticker, pred)
        if actual_ret is None:
            continue  # data harga belum lengkap — coba lagi nanti

        pred.actual_ret = actual_ret
        pred.actual_label = int(actual_ret > 0)
        pred.was_correct = pred.actual_label == pred.predicted_label
        pred.resolved_at = now

        if not pred.was_correct:
            pred.miss_reason = await _classify_miss(session, ticker, pred)
        resolved += 1

    if resolved:
        await session.commit()
    return resolved


async def _actual_return(session, ticker: str, pred: Prediction) -> float | None:
    """Return aktual dari tanggal prediksi ke akhir horizon."""
    start = pred.created_at.date()
    end = start + timedelta(days=pred.horizon_days)
    rows = await get_cached_prices(session, ticker, start, end)
    if len(rows) < 2:
        return None
    return rows[-1].close / rows[0].close - 1.0


async def _classify_miss(session, ticker: str, pred: Prediction) -> str:
    """Cek ada berita kontra-arah berdampak besar → 'event', else 'model'."""
    end = pred.created_at + timedelta(days=pred.horizon_days)
    news_rows = (
        (
            await session.execute(
                select(News).where(
                    News.ticker == ticker,
                    News.published_at > pred.created_at,
                    News.published_at <= end,
                )
            )
        )
        .scalars()
        .all()
    )

    expected_up = pred.predicted_label == 1
    for n in news_rows:
        if n.sentiment_score is None:
            continue
        contradicts = (n.sentiment_score < 0) if expected_up else (n.sentiment_score > 0)
        if contradicts and abs(n.sentiment_score) >= EVENT_SENTIMENT_THRESHOLD:
            return "event"
    return "model"
