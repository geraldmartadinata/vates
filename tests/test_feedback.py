"""Test services/feedback.py — resolve prediksi & klasifikasi miss."""

from datetime import date, datetime

import pandas as pd
import pytest

from app.models import News, Prediction
from services.feedback import resolve_pending


def _seed_prices(session, ticker, start_date, horizon_days, closes):
    """Simpan harga harian dari start_date selama horizon_days+1 hari."""

    dates = pd.date_range(start_date, periods=horizon_days + 1, freq="D")
    df = pd.DataFrame({
        "date": [d.date() for d in dates],
        "open": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "close": closes,
        "volume": [1000000] * len(closes),
    })
    from services.cache import save_prices
    return save_prices(session, ticker, df)


@pytest.mark.asyncio
async def test_resolve_after_horizon(db_session, sample_ticker):
    """Prediksi 30d lalu → harus ter-resolve."""
    start = datetime(2026, 1, 1)
    pred = Prediction(
        ticker=sample_ticker, horizon_days=30,
        predicted_prob=0.6, predicted_label=1, created_at=start,
    )
    db_session.add(pred)
    await db_session.commit()

    closes = [100 + i for i in range(31)]  # naik
    await _seed_prices(db_session, sample_ticker, date(2026, 1, 1), 30, closes)

    resolved = await resolve_pending(db_session, sample_ticker)
    assert resolved == 1

    await db_session.refresh(pred)
    assert pred.resolved_at is not None
    assert pred.actual_label == 1
    assert pred.was_correct is True


@pytest.mark.asyncio
async def test_miss_reason_model(db_session, sample_ticker):
    """Naik diprediksi tapi turun, tanpa berita → 'model'."""
    start = datetime(2026, 1, 1)
    pred = Prediction(
        ticker=sample_ticker, horizon_days=30,
        predicted_prob=0.7, predicted_label=1, created_at=start,
    )
    db_session.add(pred)
    await db_session.commit()

    closes = [100 - i for i in range(31)]  # turun
    await _seed_prices(db_session, sample_ticker, date(2026, 1, 1), 30, closes)

    await resolve_pending(db_session, sample_ticker)
    await db_session.refresh(pred)
    assert pred.was_correct is False
    assert pred.miss_reason == "model"


@pytest.mark.asyncio
async def test_miss_reason_event(db_session, sample_ticker):
    """Naik diprediksi tapi turun karena berita negatif → 'event'."""
    start = datetime(2026, 1, 1)
    pred = Prediction(
        ticker=sample_ticker, horizon_days=30,
        predicted_prob=0.7, predicted_label=1, created_at=start,
    )
    db_session.add(pred)
    db_session.add(
        News(
            ticker=sample_ticker,
            title="Perusahaan kena sanksi",
            published_at=datetime(2026, 1, 5),
            sentiment_score=-0.8,
            impact="high",
        )
    )
    await db_session.commit()

    closes = [100 - i for i in range(31)]
    await _seed_prices(db_session, sample_ticker, date(2026, 1, 1), 30, closes)

    await resolve_pending(db_session, sample_ticker)
    await db_session.refresh(pred)
    assert pred.was_correct is False
    assert pred.miss_reason == "event"


@pytest.mark.asyncio
async def test_unresolved_when_horizon_future(db_session, sample_ticker):
    """Horizon belum berakhir → tidak di-resolve."""
    pred = Prediction(
        ticker=sample_ticker, horizon_days=30,
        predicted_prob=0.5, predicted_label=1,
        created_at=datetime.utcnow(),
    )
    db_session.add(pred)
    await db_session.commit()

    resolved = await resolve_pending(db_session, sample_ticker)
    assert resolved == 0
    await db_session.refresh(pred)
    assert pred.resolved_at is None
