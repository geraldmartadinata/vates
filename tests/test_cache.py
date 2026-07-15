"""Fase RED — test untuk services/cache.py.

Skenario:
1. test_cache_miss          → query data yang belum pernah disave → []
2. test_cache_hit           → save lalu query ticker+date sama → 1 row
3. test_save_and_retrieve   → save bulk, query range → N row
4. test_cache_upsert        → save baris yg sama 2x → tetap 1 row (no dupe)
5. test_is_cache_fresh      → data baru → fresh
6. test_is_cache_stale      → data lama → stale
"""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from app.models import CachedPrice


@pytest.mark.asyncio
async def test_cache_miss(db_session, sample_ticker):
    """RED: Belum ada data → cache miss."""
    from services.cache import get_cached_prices

    result = await get_cached_prices(
        db_session, sample_ticker, date(2025, 1, 1), date(2025, 1, 31)
    )
    assert result == []


@pytest.mark.asyncio
async def test_cache_hit(db_session, sample_ticker, sample_ohlcv_df):
    """RED: Save lalu query — harus return 1 row."""
    from datetime import date
    from services.cache import get_cached_prices, save_prices

    await save_prices(db_session, sample_ticker, sample_ohlcv_df)

    # row index 2 = today - 2
    target = date.today() - timedelta(days=2)
    result = await get_cached_prices(db_session, sample_ticker, target, target)

    assert len(result) == 1
    assert result[0].ticker == sample_ticker
    assert result[0].close == 10150.0  # 10050 + 2*50


@pytest.mark.asyncio
async def test_save_and_retrieve_by_range(db_session, sample_ticker, sample_ohlcv_df):
    """RED: Save 5 baris, query seluruh range → 5 baris."""
    from datetime import date
    from services.cache import get_cached_prices, save_prices

    await save_prices(db_session, sample_ticker, sample_ohlcv_df)

    result = await get_cached_prices(
        db_session, sample_ticker, date.today() - timedelta(days=4), date.today()
    )
    assert len(result) == 5
    assert all(r.ticker == sample_ticker for r in result)


@pytest.mark.asyncio
async def test_cache_upsert(db_session, sample_ticker, sample_ohlcv_df):
    """RED: Save df yg sama 2x → tetap 5 baris (no duplicate row)."""
    from datetime import date
    from services.cache import get_cached_prices, save_prices

    await save_prices(db_session, sample_ticker, sample_ohlcv_df)
    await save_prices(db_session, sample_ticker, sample_ohlcv_df)

    result = await get_cached_prices(
        db_session, sample_ticker, date.today() - timedelta(days=4), date.today()
    )
    assert len(result) == 5


@pytest.mark.asyncio
async def test_is_cache_fresh(db_session, sample_ticker, sample_ohlcv_df):
    """RED: Data baru (today) → fresh."""
    from services.cache import is_cache_fresh, save_prices

    await save_prices(db_session, sample_ticker, sample_ohlcv_df)

    assert await is_cache_fresh(db_session, sample_ticker, max_age_days=5) is True


@pytest.mark.asyncio
async def test_is_cache_stale(db_session, sample_ticker):
    """RED: Data lama (30 hari lalu) → stale."""
    from services.cache import is_cache_fresh

    # Insert data langsung via raw SQL — tanggal kemarin-lama
    from app.database import Base
    from sqlalchemy import insert

    old_date = date.today() - timedelta(days=30)
    stmt = insert(CachedPrice).values(
        ticker=sample_ticker,
        date=datetime.combine(old_date, datetime.min.time()),
        open=10000.0, high=10100.0, low=9900.0, close=10050.0, volume=1000000,
    )
    await db_session.execute(stmt)
    await db_session.commit()

    assert await is_cache_fresh(db_session, sample_ticker, max_age_days=7) is False
