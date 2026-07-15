"""SQLite cache layer — SQLAlchemy async.

Menyediakan: get_cached_prices, save_prices, is_cache_fresh.
"""

from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CachedPrice


async def get_cached_prices(
    session: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
) -> Sequence[CachedPrice]:
    """Ambil data harga dari cache berdasarkan range tanggal.

    Args:
        session: SQLAlchemy async session.
        ticker: Ticker saham (termasuk suffix .JK).
        start_date: Tanggal awal (inclusive).
        end_date: Tanggal akhir (inclusive).

    Returns:
        List CachedPrice, sorted by date ascending.
    """
    stmt = (
        select(CachedPrice)
        .where(
            CachedPrice.ticker == ticker,
            CachedPrice.date >= datetime.combine(start_date, datetime.min.time()),
            CachedPrice.date <= datetime.combine(end_date, datetime.min.time()),
        )
        .order_by(CachedPrice.date.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def save_prices(
    session: AsyncSession,
    ticker: str,
    df,
) -> None:
    """Simpan DataFrame OHLCV ke cache.

    Delete existing rows for same ticker+dates, then insert.
    Pakai flush antara delete dan insert untuk hindari UNIQUE constraint clash.

    Args:
        session: SQLAlchemy async session.
        ticker: Ticker saham (termasuk suffix .JK).
        df: DataFrame dengan kolom date, open, high, low, close, volume.
    """
    dates_in_df = [_to_datetime(d) for d in df["date"].tolist()]
    stmt_delete = CachedPrice.__table__.delete().where(
        CachedPrice.ticker == ticker,
        CachedPrice.date.in_(dates_in_df),
    )
    await session.execute(stmt_delete)
    await session.flush()  # pastikan delete ter-eksekusi sebelum insert

    for _, row in df.iterrows():
        price = CachedPrice(
            ticker=ticker,
            date=_to_datetime(row["date"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        )
        session.add(price)

    await session.commit()


async def is_cache_fresh(
    session: AsyncSession,
    ticker: str,
    max_age_days: int = 1,
) -> bool:
    """Cek apakah cache untuk ticker ini masih fresh.

    Bandingkan tanggal data TERBARU di DB dengan hari ini - max_age_days.
    Bukan created_at — yang penting kapan data terakhir, bukan kapan di-cache.

    Args:
        session: SQLAlchemy async session.
        ticker: Ticker saham.
        max_age_days: Maksimal umur DATA dalam hari (default: 1).

    Returns:
        True jika tanggal data terbaru >= (hari ini - max_age_days).
    """
    cutoff = date.today() - timedelta(days=max_age_days)
    stmt = select(func.max(CachedPrice.date)).where(CachedPrice.ticker == ticker)
    result = await session.execute(stmt)
    max_date_val = result.scalar()

    if max_date_val is None:
        return False

    if isinstance(max_date_val, datetime):
        max_date_val = max_date_val.date()
    return max_date_val >= cutoff


def _to_datetime(val) -> datetime:
    """Konversi date/datetime/string ke datetime."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return val
